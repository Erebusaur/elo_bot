import discord
import itertools
import math
import os
import requests
import time
import trueskill
from discord.ext import commands
from dotenv import load_dotenv

bot = commands.Bot(command_prefix='?')
api = "http://localhost:5000"


class Game:
    def __init__(self, team1, team2, id=None, score=None):
        self.team1 = team1
        self.team2 = team2
        self.id = id
        self.score = score

    def to_dict(self):
        d = {}
        d["team1"] = self.team1
        d["team2"] = self.team2
        if self.id:
            d["id"] = self.id
        if self.score:
            d["score"] = self.score
        return d


def get_games(player_id: int = None):
    if player_id:
        games = requests.get(f"{api}/games?player={player_id}").json()
    else:
        games = requests.get(f"{api}/games").json()
    return games


def get_game_by_id(game_id: int):
    game = requests.get(f"{api}/games/{game_id}").json()
    return game


def get_last_game():
    game = requests.get(f"{api}/games/last").json()
    return game


def create_game(game: Game):
    print(game.to_dict())
    requests.post(f"{api}/games", json=game.to_dict())


def update_game(game):
    try:
        d = game.to_dict()
    except:
        d = game
    requests.put(f"{api}/games", json=d)


def get_rating(player_id):
    try:
        player = state.players[player_id]
    except:
        player = trueskill.Rating()
    return player.mu - 2 * player.sigma


class State:
    def __init__(self):
        self.players = {}
        self.queue = set()
        self.team_size = 4
        self.id = get_last_game()["id"]
        self.allowed_channels = [753208659865108561, 790660886242787369]


state = State()


def init_players():
    state.players = {}
    games = get_games()
    for game in games:
        team1 = game["team1"]
        team2 = game["team2"]
        score = None
        try:
            score = game["score"]
        except:
            pass
        for player in team1:
            if not player in state.players:
                state.players[player] = trueskill.Rating()
        for player in team2:
            if not player in state.players:
                state.players[player] = trueskill.Rating()
        team1_rating = list(map(lambda x: state.players[x], team1))
        team2_rating = list(map(lambda x: state.players[x], team2))
        if score == "1":
            ranks = [0, 1]
        elif score == "2":
            ranks = [1, 0]
        elif score == "D":
            ranks = [0, 0]
        else:
            continue
        team1_rating, team2_rating = trueskill.rate(
            [team1_rating, team2_rating], ranks=ranks)
        for i, player_id in enumerate(team1):
            state.players[player_id] = team1_rating[i]
        for i, player_id in enumerate(team2):
            state.players[player_id] = team2_rating[i]


@bot.event
async def on_ready():
    pass


async def start_game(ctx):
    if ctx.channel.id not in state.allowed_channels:
        return
    queue = list(state.queue)
    state.queue = set()
    state.id += 1
    size = len(queue) // 2
    best_score = 0
    best_teams = None
    for team1 in itertools.combinations(queue[1:], size - 1):
        team1 = queue[:1] + list(team1)
        team2 = [x for x in queue if x not in team1]
        team1_rating = list(map(lambda x: get_rating(x), team1))
        team2_rating = list(map(lambda x: get_rating(x), team2))
        score = trueskill.quality([team1_rating, team2_rating])
        if score > best_score:
            best_score = score
            best_teams = (team1, team2)
    team1, team2 = best_teams
    create_game(Game(team1, team2))
    mentions = ""
    description = "Team 1:\n"
    for player in team1:
        name = get_name(player)
        description += "{} {:.2f}\n".format(name, get_rating(player))
        mentions += "{} ".format(name)
    description += "\nTeam 2:\n"
    for player in team2:
        name = get_name(player)
        description += "{} {:.2f}\n".format(name, get_rating(player))
        mentions += "{} ".format(name)
    title = "Game #{} started".format(state.id)
    embed = discord.Embed(title=title, description=description)
    await ctx.send(mentions, embed=embed)


@bot.command(aliases=['j'])
async def join(ctx):
    if ctx.channel.id not in state.allowed_channels:
        return
    if ctx.author.id in state.queue:
        await ctx.send("You are already in the queue.")
        return
    state.queue.add(ctx.author.id)
    if len(state.queue) == 2 * state.team_size:
        await start_game(ctx)
    else:
        title = "[{}/{}] {} ({:.2f}) joined the queue.".format(
            len(state.queue), 2 * state.team_size, get_name(ctx.author.id), get_rating(ctx.author.id))
        embed = discord.Embed(description=title)
        await ctx.send(embed=embed)


@bot.command(aliases=['l'])
async def leave(ctx):
    if ctx.channel.id not in state.allowed_channels:
        return
    try:
        state.queue.remove(ctx.author.id)
        description = "[{}/{}] {} ({:.2f}) left the queue.".format(
            len(state.queue), 2 * state.team_size, get_name(ctx.author.id), get_rating(ctx.author.id))
        embed = discord.Embed(description=description)
        await ctx.send(embed=embed)
    except KeyError:
        await ctx.send("You are not in the queue.")
        return


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
    try:
        game = get_game_by_id(id)
    except:
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
    game["score"] = result
    update_game(game)
    init_players()

@bot.command(aliases=['cancel'])
@commands.has_any_role('Scrim Organiser', 'Moderator')
async def cancelgame(ctx, id: int):
    if ctx.channel.id not in state.allowed_channels:
        return
    try:
        game = get_game_by_id(id)
    except:
        await ctx.send("This game does not exist.")
        return
    game["score"] = 'C'
    update_game(game)
    init_players()


@bot.command(aliases=['lb'])
async def leaderboard(ctx, page=1):
    if ctx.channel.id not in state.allowed_channels:
        return
    players = list(
        map(lambda x: (x, get_rating(x)), state.players.keys()))
    players = sorted(players, key=lambda x: -x[1])
    start = 20 * (page - 1)
    if start >= len(state.players) or start < 0:
        return
    description = ""
    for (i, player) in enumerate(players[20 * (page - 1):], 1):
        if i > 20:
            break
        name = get_name(player[0])
        description += "{}: {} - `{:.2f}`\n".format(20 *
                                                    (page - 1) + i, name, player[1])
    embed = discord.Embed(title="Leaderboard", description=description)
    await ctx.send(embed=embed)


@bot.command(aliases=['q'])
async def queue(ctx):
    if ctx.channel.id not in state.allowed_channels:
        return
    title = "Queue [{}/{}]".format(len(state.queue),
                                   2 * state.team_size)
    description = "Game #{}\n".format(state.id + 1)
    for player in state.queue:
        description += "{}\n".format(get_name(player))
    embed = discord.Embed(title=title, description=description)
    await ctx.send(embed=embed)


async def _info(ctx, game):
    score = game["score"]
    title = "Game #{}".format(game["id"])
    winner = "undecided"
    if score == "1":
        winner = "team 1"
    elif score == "2":
        winner = "team 2"
    elif score == "D":
        winner = "draw"
    elif score == "C":
        winner = "cancelled"
    description = "Winner: {}\n\nTeam 1:".format(winner)
    for player in game["team1"]:
        description += "\n{}".format(get_name(player))
    description += "\n\nTeam 2:"
    for player in game["team2"]:
        description += "\n{}".format(get_name(player))
    embed = discord.Embed(title=title, description=description)
    await ctx.send(embed=embed)


@bot.command()
async def lastgame(ctx):
    game = get_last_game()
    await _info(ctx, game)


@bot.command()
async def gameinfo(ctx, id: int):
    game = get_game_by_id(id)
    await _info(ctx, game)


@bot.command()
async def info(ctx, user: discord.User = None):
    if not user:
        user = ctx.author
    games = get_games(user.id)
    wins = 0
    losses = 0
    draws = 0
    for game in games:
        score = game["score"]
        if score == "1":
            if user.id in game["team1"]:
                wins += 1
            else:
                losses += 1
        elif score == "2":
            if user.id in game["team2"]:
                wins += 1
            else:
                losses += 1
        elif score == "D":
            draws += 1
    try:
        rating = state.players[user.id]
        mu = rating.mu
        sigma = rating.sigma
    except KeyError:
        mu = 25
        sigma = 25 / 3
    rating = mu - 2 * sigma
    title = "{}'s stats".format(user.display_name)
    description = "Rating: {:.2f} ({:.2f}±{:.2f})\n".format(
        rating, mu, sigma)
    description += f"Wins: {wins}\n"
    description += f"Losses: {losses}\n"
    description += f"Draws: {draws}\n"
    description += "Games: {}\n".format(wins + losses + draws)
    embed = discord.Embed(title=title, description=description)
    await ctx.send(embed=embed)


@bot.command()
async def gamelist(ctx, user: discord.User = None):
    if user:
        title = "{}'s last games".format(user.display_name)
        last_games = get_games(user.id)[-20:][::-1]
        description = ""
        for game in last_games:
            try:
                score = game["score"]
            except:
                score = None
            id = game["id"]
            result = "undecided"
            if score == "1":
                if user.id in game["team1"]:
                    result = "win"
                else:
                    result = "loss"
            elif score == "2":
                if user.id in game["team2"]:
                    result = "win"
                else:
                    result = "loss"
            elif score == "D":
                result = "draw"
            elif score == "C":
                result = "cancelled"
            description += "Game #{}: {}\n".format(id, result)
    else:
        title = "Last games"
        last_games = get_games()[-20:][::-1]
        description = ""
        for game in last_games:
            try:
                score = game["score"]
            except:
                score = None
            id = game["id"]
            result = "undecided"
            if score == "1":
                result = "team 1"
            elif score == "2":
                result = "team 2"
            elif score == "D":
                result = "draw"
            elif score == "C":
                result = "cancelled"
            description += "Game #{}: {}\n".format(id, result)
    embed = discord.Embed(title=title, description=description)
    await ctx.send(embed=embed)


def get_name(user_id):
    return "<@" + str(user_id) + ">"


init_players()
load_dotenv()
while True:
    try:
        requests.get(api)
        break
    except:
        print("Could not connect to the api, retrying in 1 second.")
        time.sleep(1)
bot.run(os.getenv('DISCORD_TOKEN'))
