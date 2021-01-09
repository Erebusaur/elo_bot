using Microsoft.EntityFrameworkCore;

namespace Models
{
    public class Match
    {
        public long Id { get; set; }
        public long GameId { get; set; }
        public long Player { get; set; }
        public int Team { get; set; }
    }

    public class MatchContext : DbContext
    {
        public DbSet<Match> Matches { get; set; }

        protected override void OnConfiguring(DbContextOptionsBuilder optionsBuilder)
        {
            optionsBuilder.UseSqlite("Data Source=elo.db");
        }
    }
}
