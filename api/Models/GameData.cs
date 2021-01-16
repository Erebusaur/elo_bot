using Microsoft.EntityFrameworkCore;

namespace Models
{
    public class GameData
    {
        public long Id { get; set; }
        public string Date { get; set; }
    }

    public class GameDataContext : DbContext
    {
        public DbSet<GameData> GameDatas { get; set; }

        protected override void OnConfiguring(DbContextOptionsBuilder optionsBuilder)
        {
            optionsBuilder.UseSqlite("Data Source=elo.db");
        }
    }
}
