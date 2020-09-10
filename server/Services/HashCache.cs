using System;
using System.Collections.Generic;

namespace server.Services
{
    public class HashCache
    {
        DateTime CurrentDay;
        Dictionary<string, CacheEntry> Cache = new Dictionary<string, CacheEntry>();

        public HashCache()
        {
            Init();
        }

        void Init()
        {
            Cache.Clear();
            CurrentDay = DateTime.Now.Date;
        }

        public void Process(LogEntry entry)
        {
            lock (Cache)
            {
                if (CurrentDay != DateTime.Now.Date)
                    Init();

                if (!Cache.ContainsKey(entry.Zone))
                    Cache.Add(entry.Zone, new CacheEntry());
                var set = Cache[entry.Zone];
                if (entry.IsExit)
                    (entry.IsStudent ? set.CurrentStudents : set.CurrentEmployees).Remove(entry.Hash);
                else
                    (entry.IsStudent ? set.CurrentStudents : set.CurrentEmployees).Add(entry.Hash);
                (entry.IsStudent ? set.HistoryStudents : set.HistoryEmployees).Add(entry.Hash);
            }
        }

        public SummaryEntry GetCurrent(string zone)
        {
            return new SummaryEntry
            {
                Date = DateTime.Now,
                Students = Cache[zone].CurrentStudents.Count,
                Employees = Cache[zone].CurrentEmployees.Count,
                TotalEmployees = Cache[zone].HistoryEmployees.Count,
                TotalStudents = Cache[zone].HistoryStudents.Count
            };
        }
    }

    public class SummaryEntry
    {
            public DateTime Date {get;set;}
            public int Students { get;set;}
            public int Employees {get;set;}
            public int TotalStudents {get;set;}
            public int TotalEmployees {get;set;}
    }

    public class CacheEntry
    {
        public HashSet<string> CurrentStudents {get;} = new HashSet<string>();
        public HashSet<string> HistoryStudents {get;} = new HashSet<string>();
        public HashSet<string> CurrentEmployees {get;} = new HashSet<string>();
        public HashSet<string> HistoryEmployees {get;} = new HashSet<string>();
    } 
}