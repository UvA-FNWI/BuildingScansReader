using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using server.Services;

namespace server.Controllers
{
    [ApiController]
    [Route("[controller]")]
    public class LogController : ControllerBase
    {
        private readonly ILogger<LogController> _logger;
        private readonly HashCache _cache;
        private readonly IConfiguration _config;

        public LogController(ILogger<LogController> logger, HashCache cache, IConfiguration config)
        {
            _logger = logger;
            _cache = cache;
            _config = config;
        }

        [HttpPost]
        public IActionResult Post(LogEntry entry)
        {
            var client = new HttpClient();
            _cache.Process(entry);
            client.PostAsync(_config[$"Endpoints:{entry.Zone}"], 
                new StringContent(JsonSerializer.Serialize(_cache.GetCurrent(entry.Zone)), 
                    Encoding.UTF8, "application/json"));
            return Ok();
        }
    }
}
