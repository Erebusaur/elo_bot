class Game:
    def __init__(self, team1, team2, id=None, score=None, date=None):
        self.team1 = team1
        self.team2 = team2
        self.id = id
        self.score = score
        self.date = date

    def to_dict(self) -> dict:
        d = {"team1": self.team1, "team2": self.team2}
        if self.id:
            d["id"] = self.id
        if self.score:
            d["score"] = self.score
        if self.date:
            d["date"] = self.date
        return d
