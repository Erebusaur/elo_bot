using Microsoft.EntityFrameworkCore;

namespace Models
{
    public class Score
    {
        public long Id { get; set; }
        public long GameId { get; set; }
        public float? Result { get; set; }
    }

    public class ScoreContext : DbContext
    {
        public DbSet<Score> Scores { get; set; }

        protected override void OnConfiguring(DbContextOptionsBuilder optionsBuilder)
        {
            optionsBuilder.UseSqlite("Data Source=elo.db");
        }
    }
}
