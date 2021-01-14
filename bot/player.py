import trueskill

class Player:
    def __init__(self, rating = trueskill.Rating()):
        self.rating = rating
        self.wins = 0
        self.losses = 0
        self.draws = 0
