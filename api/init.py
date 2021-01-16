import sqlite3

conn = sqlite3.connect('elo.db')
cur = conn.cursor()

cur.execute("DROP TABLE IF EXISTS matches;")
cur.execute("DROP TABLE IF EXISTS scores;")
cur.execute("DROP TABLE IF EXISTS gamedatas;")

cur.execute("CREATE TABLE IF NOT EXISTS matches(id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, gameid INTEGER NOT NULL, player INTEGER NOT NULL, team INTEGER NOT NULL);")
cur.execute(
    "CREATE TABLE IF NOT EXISTS scores (id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, gameid INTEGER NOT NULL, result REAL);")
cur.execute("CREATE TABLE gamedatas (id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, date TEXT);")

def score(result):
    if result == 'W':
        return 1
    elif result == 'L':
        return 0
    elif result == 'D':
        return 0.5
    return None


scores = {}
with open("data/scores.csv") as scores_file:
    sql_scores = 'INSERT INTO scores (gameid, result) VALUES (?, ?);'
    sql_gamedatas = 'INSERT INTO gamedatas (id, date) VALUES (?, ?);'
    for line in scores_file:
        if line.startswith('#'):
            continue
        values = line.split(',')
        id = int(values[0])
        score = values[1].strip()
        if score == '1' or score == 'W':
            score = 1
        elif score == '2' or score == 'L':
            score = 0
        else:
            score = 0.5
        scores[id] = score
        cur.execute(sql_scores, (id, scores[id]))
        cur.execute(sql_gamedatas, (id, '1970-01-01 00:00:00Z'))



with open("data/games.csv") as games_file:
    sql_games = 'INSERT INTO matches (gameid, player, team) VALUES (?, ?, ?);'
    for line in games_file.readlines():
        if line.startswith('#'):
            continue
        values = line.split(',')
        id = int(values[0])
        team = int(values[1])
        player_id = int(values[2])
        cur.execute(sql_games, (id, player_id, team))


conn.commit()


conn.close()
