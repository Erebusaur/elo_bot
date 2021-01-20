from api import Api
from game import Game
from player import Player
from typing import Optional
import trueskill


class State:
    def __init__(self, api: Api):
        self.api = api
        self.players = {}
        self.queue = set()
        self.team_size = 4
        self.frozen = False
        self.allowed_channels = [753208659865108561,
                                 790660886242787369, 739093044346748948]

    def update_players(self) -> None:
        games = self.api.get_games()
        players = {}
        for game in games:
            update_ratings(players, game)
        self.players = players

    def add_queue(self, player_id: int) -> None:
        if player_id in self.queue:
            raise KeyError
        self.queue.add(player_id)

    def remove_queue(self, player_id: int) -> None:
        self.queue.remove(player_id)

    def get_player(self, player_id: int) -> Optional[Player]:
        return self.players.get(player_id)

    def get_rating(self, player_id: int) -> trueskill.Rating:
        player = self.get_player(player_id)
        if player:
            return player.rating
        else:
            return trueskill.Rating()

    def get_conservative_rating(self, player_id: int) -> int:
        rating = self.get_rating(player_id)
        return round(100 * (rating.mu - 2 * rating.sigma))


def update_ratings(players: dict, game: Game) -> None:
    if not game.score:
        return
    if game.score == '1':
        ranks = [0, 1]
    elif game.score == '2':
        ranks = [1, 0]
    elif game.score == 'D':
        ranks = [0, 0]
    else:
        return
    for player_id in game.team1:
        if not player_id in players:
            players[player_id] = Player()
    for player_id in game.team2:
        if not player_id in players:
            players[player_id] = Player()
    team1_ratings = list(map(lambda id: players[id].rating, game.team1))
    team2_ratings = list(map(lambda id: players[id].rating, game.team2))
    team1_ratings, team2_ratings = trueskill.rate(
        [team1_ratings, team2_ratings], ranks=ranks)
    for i, player in enumerate(game.team1):
        players[player].rating = team1_ratings[i]
    for i, player in enumerate(game.team2):
        players[player].rating = team2_ratings[i]
