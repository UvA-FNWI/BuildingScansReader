using System;

namespace server
{
    public class LogEntry
    {
        /// <summary>
        /// Hash of the card number
        /// </summary>
        public string Hash { get; set; }

        /// <summary>
        /// True for check-out, false for check-in
        /// </summary>
        public bool IsExit { get; set; }

        /// <summary>
        /// Is the user a student or employee?
        /// </summary>
        public bool IsStudent { get; set; }

        /// <summary>
        /// Building zone, for now C or G
        /// </summary>
        public string Zone { get; set; }
    }
}
