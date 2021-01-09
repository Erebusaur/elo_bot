using System.Collections.Generic;

namespace Models
{
    public class Game
    {
        public long Id { get; set; }
        public List<long> Team1 { get; set; }
        public List<long> Team2 { get; set; }

        public char? Score { get; set; }

    }
}
