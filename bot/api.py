import requests
from typing import Optional, List
from game import Game


class Api:
    def __init__(self, url: str):
        self.url = url

    def get_games(self, player_id: int = None) -> List[Game]:
        url = f"{self.url}/games"
        if player_id:
            url += f"?player={player_id}"
        return list(map(dict2game, requests.get(url).json()))

    def get_game_by_id(self, game_id: int) -> Optional[Game]:
        r = requests.get(f"{self.url}/games/{game_id}")
        if r.status_code == 200:
            return dict2game(r.json())
        else:
            return None

    def get_last_game(self) -> Optional[Game]:
        r = requests.get(f"{self.url}/games/last")
        if r.status_code == 200:
            return dict2game(r.json())
        else:
            return None

    def create_game(self, game: Game) -> None:
        requests.post(f"{self.url}/games", json=game.to_dict())

    def update_game(self, game: Game) -> None:
        requests.put(f"{self.url}/games", json=game.to_dict())


def dict2game(x: dict) -> Game:
    return Game(x["team1"], x["team2"], x.get("id"), x.get("score"))
