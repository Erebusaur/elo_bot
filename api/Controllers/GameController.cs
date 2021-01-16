using System.Collections.Generic;
using System.Linq;
using System.Net.Mime;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Models;
using System;

namespace Controllers
{
    [ApiController]
    [Produces(MediaTypeNames.Application.Json)]
    [Route("[controller]")]
    public class GamesController : ControllerBase
    {

        private Game createGame(IEnumerable<Match> matches, float? score, long id, DateTime date)
        {
            char? result = null;
            if (score == 0)
            {
                result = '2';
            }
            else if (score == 1)
            {
                result = '1';
            }
            else if (score == 0.5)
            {
                result = 'D';
            }
            else if (score == -1)
            {
                result = 'C';
            }
            var team1 = new List<long>();
            var team2 = new List<long>();
            foreach (var match in matches)
            {
                if (match.Team == 1)
                {
                    team1.Add(match.Player);
                }
                else
                {
                    team2.Add(match.Player);
                }
            }
            return new Game
            {
                Id = id,
                Team1 = team1,
                Team2 = team2,
                Score = result,
                Date = date.ToString("u", System.Globalization.CultureInfo.InvariantCulture),
            };
        }

        public List<Game> all()
        {
            using var gameDataContext = new GameDataContext();
            var gameDatas = gameDataContext.GameDatas;
            using var matchContext = new MatchContext();
            var matchesByGameId = matchContext
                .Matches
                .AsEnumerable()
                .GroupBy(m => m.GameId)
                .ToDictionary(g => g.Key, g => g.ToList());
            using var scoreContext = new ScoreContext();
            var scores = scoreContext.Scores.ToDictionary(g => g.Id, g => g);
            var games = new List<Game>();
            foreach (var gameData in gameDatas)
            {
                var id = gameData.Id;
                var score = scores[id];
                var matches = matchesByGameId[id];
                DateTime date = DateTime.ParseExact(gameData.Date, "u", System.Globalization.CultureInfo.InvariantCulture);
                games.Add(createGame(matches, score?.Result, id, date));
            }
            return games;
        }

        [HttpGet("{id}")]
        public ActionResult<Game> GetById(int id)
        {
            using var gameDataContext  = new GameDataContext();
            var gameData = gameDataContext.GameDatas.Where(x => x.Id == id).FirstOrDefault();
            if (gameData == null)
            {
                return NotFound();
            }
            using var matchContext = new MatchContext();
            var matches = matchContext.Matches.Where(x => x.GameId == id);
            using var scoreContext = new ScoreContext();
            var score = scoreContext.Scores.Where(x => x.GameId == id).FirstOrDefault();
            DateTime date = DateTime.ParseExact(gameData.Date, "u", System.Globalization.CultureInfo.InvariantCulture);
            return createGame(matches, score?.Result, id, date);
        }

        [HttpGet]
        public ActionResult<List<Game>> GetByPlayer(long? player)
        {
            var games = all();
            if (player != null)
            {
                games = games.Where(x => x.Team1.Contains(player.Value) || x.Team2.Contains(player.Value)).ToList();
            }
            return games;
        }

        [HttpGet("last")]
        public ActionResult<Game> GetLast()
        {
            var games = all();
            if (games.Count == 0)
            {
                return NotFound();
            }
            return games.Last();
        }

        [HttpPost]
        public ActionResult<Game> Create(Game game)
        {
            using var gameDataContext = new GameDataContext();
            using var matchContext = new MatchContext();
            long id = (gameDataContext.GameDatas.Max(m => (int?)m.Id) ?? 0) + 1;
            game.Id = id;
            if (game.Date == null)
            {
                game.Date = DateTime.Now.ToString("u", System.Globalization.CultureInfo.InvariantCulture);
            }
            gameDataContext.Add(new GameData {
                Id = id,
                Date = game.Date,
            });
            gameDataContext.SaveChanges();
            var matches = new List<Match>();
            foreach (var player in game.Team1)
            {
                matches.Add(new Match
                {
                    GameId = id,
                    Player = player,
                    Team = 1,
                });
            }
            foreach (var player in game.Team2)
            {
                matches.Add(new Match
                {
                    GameId = id,
                    Player = player,
                    Team = 2,
                });
            }
            matchContext.AddRange(matches);
            matchContext.SaveChanges();
            using var scoreContext = new ScoreContext();
            float? result = null;
            if (game.Score == '1')
            {
                result = 1;
            }
            else if (game.Score == '2')
            {
                result = 0;
            }
            else if (game.Score == 'D')
            {
                result = 0.5f;
            }
            else if (game.Score == 'C')
            {
                result = -1;
            }
            scoreContext.Add(new Score
            {
                GameId = id,
                Result = result,
            });
            scoreContext.SaveChanges();
            return CreatedAtAction(nameof(GetById), new { id = id }, game);
        }

        [HttpPut]
        public ActionResult<Game> Update(Game game)
        {
            using var gameDataContext = new GameDataContext();
            var gameData = gameDataContext.GameDatas.Where(g => g.Id == game.Id).SingleOrDefault();
            gameData.Date = game.Date;
            gameDataContext.SaveChanges();
            using var matchContext = new MatchContext();
            var matches = matchContext.Matches.Where(m => m.GameId == game.Id);
            matchContext.Matches.RemoveRange(matches);
            foreach (var player in game.Team1)
            {
                matchContext.Add(new Match
                {
                    GameId = game.Id,
                    Player = player,
                    Team = 1,
                });
            }
            foreach (var player in game.Team2)
            {
                matchContext.Add(new Match
                {
                    GameId = game.Id,
                    Player = player,
                    Team = 2,
                });
            }
            matchContext.SaveChanges();
            using var scoreContext = new ScoreContext();
            var score = scoreContext.Scores.Where(s => s.GameId == game.Id).Single();
            if (game.Score == '1')
            {
                score.Result = 1f;
            }
            else if (game.Score == '2')
            {
                score.Result = 0f;
            }
            else if (game.Score == 'D')
            {
                score.Result = 0.5f;
            }
            else if (game.Score == 'C')
            {
                score.Result = -1f;
            }
            else
            {
                score.Result = null;
            }
            scoreContext.SaveChanges();
            return CreatedAtAction(nameof(GetById), new { id = game.Id }, game);
        }
    }
}
