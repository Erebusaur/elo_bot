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

        private Game createGame(IEnumerable<Match> matches, float? score, long id)
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
            };
        }

        public List<Game> all()
        {
            using var matchContext = new MatchContext();
            var matchesByGameId = matchContext
                .Matches
                .AsEnumerable()
                .GroupBy(m => m.GameId)
                .ToDictionary(g => g.Key, g => g.ToList());
            using var scoreContext = new ScoreContext();
            var scores = scoreContext.Scores;
            var games = new List<Game>();
            foreach (var score in scores)
            {
                var id = score.GameId;
                var matches = matchesByGameId[id];
                games.Add(createGame(matches, score?.Result, id));
            }
            return games;
        }

        [HttpGet("{id}")]
        public ActionResult<Game> GetById(int id)
        {
            using var matchContext = new MatchContext();
            var matches = matchContext.Matches.Where(x => x.GameId == id);
            using var scoreContext = new ScoreContext();
            var score = scoreContext.Scores.Where(x => x.GameId == id).FirstOrDefault();
            if (matches.Count() == 0)
            {
                return NotFound();
            }
            return createGame(matches, score?.Result, id);
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
            using var matchContext = new MatchContext();
            long id = (matchContext.Matches.Max(m => (int?)m.GameId) ?? 0) + 1;
            game.Id = id;
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
            using var matchContext = new MatchContext();
            var matches = matchContext.Matches.Where(m => m.GameId == game.Id);
            if (matches.Count() == 0)
            {
                return NotFound();
            }
            matchContext.Matches.RemoveRange(matches);
            matchContext.SaveChanges();
            using var scoreContext = new ScoreContext();
            var score = scoreContext.Scores.Where(s => s.GameId == game.Id).Single();
            scoreContext.Scores.Remove(score);
            scoreContext.SaveChanges();
            return Create(game);
        }
    }
}
