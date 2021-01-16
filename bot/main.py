import discord
import itertools
import math
import os
import requests
import time
import trueskill
from discord.ext import commands
from dotenv import load_dotenv

from state import State
from api import Api
from game import Game
from player import Player

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix='?', intents=intents)


@bot.event
async def on_ready():
    pass


async def start_game(ctx):
    if ctx.channel.id not in state.allowed_channels:
        return
    queue = list(state.queue)
    state.queue = set()
    size = state.team_size
    best_score = 0
    best_teams = None
    for team1 in itertools.combinations(queue[1:], size - 1):
        team1 = queue[:1] + list(team1)
        team2 = [x for x in queue if x not in team1]
        team1_rating = list(map(lambda id: state.get_rating(id), team1))
        team2_rating = list(map(lambda id: state.get_rating(id), team2))
        score = trueskill.quality([team1_rating, team2_rating])
        if score > best_score:
            best_score = score
            best_teams = (team1, team2)
    team1, team2 = best_teams
    state.api.create_game(Game(team1, team2))
    mentions = ""
    description = "Team 1:\n"
    for player_id in team1:
        member = ctx.guild.get_member(player_id)
        name = member.mention
        rating = state.get_conservative_rating(player_id)
        description += "{} {}\n".format(name, rating)
        mentions += "{} ".format(name)
    description += "\nTeam 2:\n"
    for player_id in team2:
        member = ctx.guild.get_member(player_id)
        name = member.mention
        rating = state.get_conservative_rating(player_id)
        description += "{} {}\n".format(name, rating)
        mentions += "{} ".format(name)
    last_game = state.api.get_last_game()
    if last_game:
        id = last_game.id + 1
    else:
        id = 1
    title = "Game #{} started".format(id)
    embed = discord.Embed(title=title, description=description)
    message = await ctx.send(mentions, embed=embed)
    for player_id in team1:
        try:
            member = ctx.guild.get_member(player_id)
            await member.send("Game started: {}".format(message.jump_url))
        except:
            pass
    for player_id in team2:
        try:
            member = ctx.guild.get_member(player_id)
            await member.send("Game started: {}".format(message.jump_url))
        except:
            pass



async def add_player(ctx, player: discord.User):
    name = player.mention
    try:
        state.add_queue(player.id)
    except KeyError:
        await ctx.send(f"{name} is already in the queue.")
        return
    rating = state.get_conservative_rating(player.id)
    title = "[{}/{}] {} ({}) joined the queue.".format(
        len(state.queue), 2 * state.team_size, name, rating)
    embed = discord.Embed(description=title)
    await ctx.send(embed=embed)
    if len(state.queue) == 2 * state.team_size:
        await start_game(ctx)


@bot.command(aliases=['j'])
async def join(ctx):
    if ctx.channel.id not in state.allowed_channels:
        return
    await add_player(ctx, ctx.author)


@bot.command()
@commands.has_any_role('Scrim Organiser', 'Moderator')
async def forcejoin(ctx, user: discord.User):
    if ctx.channel.id not in state.allowed_channels:
        return
    await add_player(ctx, user)


async def remove_player(ctx, player: discord.User):
    name = player.mention
    try:
        state.remove_queue(player.id)
    except KeyError:
        await ctx.send(f"{name} is not in the queue.")
        return
    rating = state.get_conservative_rating(player.id)
    description = "[{}/{}] {} ({}) left the queue.".format(
        len(state.queue), 2 * state.team_size, name, rating)
    embed = discord.Embed(description=description)
    await ctx.send(embed=embed)
    if len(state.queue) == 2 * state.team_size:
        await start_game(ctx)


@bot.command(aliases=['l'])
async def leave(ctx):
    if ctx.channel.id not in state.allowed_channels:
        return
    await remove_player(ctx, ctx.author)


@bot.command()
@commands.has_any_role('Scrim Organiser', 'Moderator')
async def forceremove(ctx, user: discord.User):
    if ctx.channel.id not in state.allowed_channels:
        return
    await remove_player(ctx, user)


@bot.command()
@commands.has_any_role('Scrim Organiser', 'Moderator')
async def players(ctx, n: int):
    if ctx.channel.id not in state.allowed_channels:
        return
    if n < 1:
        await ctx.send("First argument must be greater than 1.")
        return
    state.team_size = n
    await ctx.send(f"Players per team set to {n}.")
    if len(state.queue) == 2 * state.team_size:
        await start_game(ctx)


@bot.command(aliases=['g'])
@commands.has_any_role('Scrim Organiser', 'Moderator')
async def score(ctx, id: int, team: str):
    if ctx.channel.id not in state.allowed_channels:
        return
    game = state.api.get_game_by_id(id)
    if not game:
        await ctx.send("This game does not exist.")
        return
    if team == '1':
        result = '1'
    elif team == '2':
        result = '2'
    elif team == 'draw':
        result = 'D'
    else:
        await ctx.send("Score must be 1, 2 or draw.")
        return
    game.score = result
    state.api.update_game(game)
    state.update_players()


@bot.command(aliases=['cancel'])
@commands.has_any_role('Scrim Organiser', 'Moderator')
async def cancelgame(ctx, id: int):
    if ctx.channel.id not in state.allowed_channels:
        return
    game = state.api.get_game_by_id(id)
    if not game:
        await ctx.send("This game does not exist.")
        return
    game["score"] = 'C'
    state.api.update_game(game)
    state.update_players()


@bot.command(aliases=['lb'])
async def leaderboard(ctx, page=1):
    if ctx.channel.id not in state.allowed_channels:
        return
    players = list(
        filter(lambda x: x[0], map(lambda x: (ctx.guild.get_member(x), state.get_conservative_rating(x)), state.players.keys())))
    players = sorted(players, key=lambda x: -x[1])
    pages = math.ceil(len(players) / 20)
    if page > pages:
        return
    start = 20 * (page - 1)
    description = ""
    for (i, player) in enumerate(players[start:start+20], start + 1):
        name = player[0]
        description += "{}: {} - `{}`\n".format(
            i, name.mention, player[1])
    embed = discord.Embed(
        title=f"Leaderboard ({page}/{pages})", description=description)
    await ctx.send(embed=embed)


@bot.command(aliases=['q'])
async def queue(ctx):
    if ctx.channel.id not in state.allowed_channels:
        return
    last_game = state.api.get_last_game()
    if last_game:
        id = last_game.id + 1
    else:
        id = 1
    title = "Game #{} [{}/{}]".format(id, len(state.queue),
                                      2 * state.team_size)
    description = ""
    for player_id in state.queue:
        name = ctx.guild.get_member(player_id).mention
        rating = state.get_conservative_rating(player_id)
        description += "{} ({})\n".format(name, rating)
    embed = discord.Embed(title=title, description=description)
    await ctx.send(embed=embed)


async def _gameinfo(ctx, game: Game):
    title = "Game #{}".format(game.id)
    winner = "undecided"
    if game.score == "1":
        winner = "team 1"
    elif game.score == "2":
        winner = "team 2"
    elif game.score == "D":
        winner = "draw"
    elif game.score == "C":
        winner = "cancelled"
    description = "{}\n\nWinner: {}\n\nTeam 1:".format(game.date[:-1], winner)
    for player in game.team1:
        name = "<@" + str(player) + ">"
        description += "\n{}".format(name)
    description += "\n\nTeam 2:"
    for player in game.team2:
        name = "<@" + str(player) + ">"
        description += "\n{}".format(name)
    embed = discord.Embed(title=title, description=description)
    await ctx.send(embed=embed)


@bot.command()
async def lastgame(ctx):
    if ctx.channel.id not in state.allowed_channels:
        return
    game = state.api.get_last_game()
    if not game:
        await ctx.send("No game was played.")
        return
    await _gameinfo(ctx, game)


@bot.command()
async def gameinfo(ctx, id: int):
    if ctx.channel.id not in state.allowed_channels:
        return
    game = state.api.get_game_by_id(id)
    if not game:
        await ctx.send("This game does not exist.")
        return
    await _gameinfo(ctx, game)


@bot.command()
async def info(ctx, user: discord.User = None):
    if ctx.channel.id not in state.allowed_channels:
        return
    if not user:
        user = ctx.author
    games = state.api.get_games(user.id)
    wins = 0
    losses = 0
    draws = 0
    for game in games:
        if game.score == "1":
            if user.id in game.team1:
                wins += 1
            else:
                losses += 1
        elif game.score == "2":
            if user.id in game.team2:
                wins += 1
            else:
                losses += 1
        elif game.score == "D":
            draws += 1
    rating = state.get_rating(user.id)
    mu = round(100 * rating.mu)
    sigma = round(200 * rating.sigma)
    rating = state.get_conservative_rating(user.id)
    title = "{}'s stats".format(user.display_name)
    description = "Rating: {} ({}±{})\n".format(
        rating, mu, sigma)
    description += f"Wins: {wins}\n"
    description += f"Losses: {losses}\n"
    description += f"Draws: {draws}\n"
    description += "Games: {}\n".format(wins + losses + draws)
    embed = discord.Embed(title=title, description=description)
    await ctx.send(embed=embed)


@bot.command()
async def gamelist(ctx, user: discord.User = None):
    if ctx.channel.id not in state.allowed_channels:
        return
    if user:
        title = "{}'s last games".format(user.display_name)
        last_games = state.api.get_games(user.id)[-20:][::-1]
        description = ""
        for game in last_games:
            result = "undecided"
            if game.score == "1":
                if user.id in game.team1:
                    result = "win"
                else:
                    result = "loss"
            elif game.score == "2":
                if user.id in game.team2:
                    result = "win"
                else:
                    result = "loss"
            elif game.score == "D":
                result = "draw"
            elif game.score == "C":
                result = "cancelled"
            description += "Game #{}: {}\n".format(game.id, result)
    else:
        title = "Last games"
        last_games = state.api.get_games()[-20:][::-1]
        description = ""
        for game in last_games:
            result = "undecided"
            if game.score == "1":
                result = "team 1"
            elif game.score == "2":
                result = "team 2"
            elif game.score == "D":
                result = "draw"
            elif game.score == "C":
                result = "cancelled"
            description += "Game #{}: {}\n".format(game.id, result)
    embed = discord.Embed(title=title, description=description)
    await ctx.send(embed=embed)


@bot.command()
async def stats(ctx):
    if ctx.channel.id not in state.allowed_channels:
        return
    games = state.api.get_games()
    total_games = len(games)
    draws = 0
    cancelled = 0
    ongoing = 0
    for game in games:
        if game.score == "C":
            cancelled_games += 1
        elif game.score == "D":
            draws += 1
        elif not game.score:
            ongoing += 1
    title = "Stats"
    description = "Total games: {}\n".format(total_games)
    description += "Games played: {}\n".format(
        total_games - cancelled - ongoing)
    description += "Cancelled games: {}\n".format(cancelled)
    description += "Ongoing games: {}\n".format(ongoing)
    # description += "Draws: {}\n".format(draws)
    embed = discord.Embed(title=title, description=description)
    await ctx.send(embed=embed)


@bot.command()
async def swap(ctx, user1: discord.User, user2: discord.User):
    if ctx.channel.id not in state.allowed_channels:
        return
    game = state.api.get_last_game()
    if user1.id in game.team1:
        if user2.id in game.team1:
            await ctx.send("These players are on the same team.")
            return
        elif user2.id in game.team2:
            game.team1 = [x if x != user1.id else user2.id for x in game.team1]
            game.team2 = [x if x != user2.id else user1.id for x in game.team2]
        else:
            game.team1 = [x if x != user1.id else user2.id for x in game.team1]
    elif user1.id in game.team2:
        if user2.id in game.team2:
            await ctx.send("These players are on the same team.")
            return
        elif user2.id in game.team1:
            game.team1 = [x if x != user2.id else user1.id for x in game.team1]
            game.team2 = [x if x != user1.id else user2.id for x in game.team2]
        else:
            game.team2 = [x if x != user1.id else user2.id for x in game.team2]
    else:
        await ctx.send("{} is not playing.".format(user1.mention))
        return
    state.api.update_game(game)
    await ctx.send("Players swapped.")
    if game.score in ["1", "2", "D"]:
        state.update_players()


def get_name(user_id):
    return "<@" + str(user_id) + ">"


load_dotenv()
api = Api("http://localhost:5000")
state = State(api)
state.update_players()
bot.run(os.getenv('DISCORD_TOKEN'))
