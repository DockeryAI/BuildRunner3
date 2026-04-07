# API Debugging Guide

Guide for debugging and troubleshooting the BuildRunner 3.0 API.

## Debug Endpoints

The API includes several debug endpoints for monitoring and troubleshooting.

### System Health Check

```bash
curl http://localhost:8000/debug/status
```

Returns comprehensive system diagnostics:
- Overall health status (healthy/degraded/critical)
- API uptime
- Number of features loaded
- Background test runner status
- Error count
- Active issues list

**Health Status Levels:**
- **healthy**: No critical errors, system functioning normally
- **degraded**: Some errors present but system operational
- **critical**: Critical errors detected, system may be unstable

### Error Monitoring

#### View All Errors

```bash
curl http://localhost:8000/debug/errors
```

#### Filter by Category

```bash
curl "http://localhost:8000/debug/errors?category=syntax"
curl "http://localhost:8000/debug/errors?category=runtime"
curl "http://localhost:8000/debug/errors?category=test"
```

**Error Categories:**
- `syntax` - Python syntax errors
- `runtime` - Runtime exceptions (TypeError, AttributeError, etc.)
- `test` - Test failures
- `import` - Import/module not found errors
- `type` - Type checking errors
- `network` - Connection/timeout errors

#### Filter by Severity

```bash
curl "http://localhost:8000/debug/errors?severity=critical"
curl "http://localhost:8000/debug/errors?severity=high"
```

#### View Only Unresolved Errors

```bash
curl "http://localhost:8000/debug/errors?unresolved_only=true"
```

### Background Test Runner

#### Check Test Runner Status

```bash
curl http://localhost:8000/test/status
```

Shows:
- Whether test runner is active
- Test run interval
- Number of connected WebSocket clients
- Latest test results

#### Run Tests Immediately

```bash
curl -X POST http://localhost:8000/debug/test
```

Executes pytest and returns full results without waiting for scheduled run.

#### Start Background Testing

```bash
curl -X POST "http://localhost:8000/test/start?interval=120"
```

Runs tests every 120 seconds and broadcasts results via WebSocket.

#### Stop Background Testing

```bash
curl -X POST http://localhost:8000/test/stop
```

### Request Logging

All API requests are automatically logged with:
- Timestamp
- HTTP method
- Request path
- Response status code
- Duration in milliseconds

Slow requests (>1 second) are logged with a warning.

Check response headers for performance data:
```bash
curl -i http://localhost:8000/features
```

Look for `X-Response-Time` header.

## Error Watcher

The error watcher automatically monitors `.buildrunner/context/` for errors and categorizes them.

### How It Works

1. Scans context files every 30 seconds (by default)
2. Matches error patterns using regex
3. Categorizes errors by type and severity
4. Extracts file paths and line numbers
5. Provides fix suggestions based on error type
6. Avoids duplicate error reporting

### Error Pattern Matching

The error watcher recognizes these patterns:
- `SyntaxError:` - Python syntax issues
- `IndentationError:` - Indentation problems
- `ModuleNotFoundError:` - Missing packages
- `TypeError:` - Type mismatches
- `AttributeError:` - Missing attributes
- `KeyError:` - Dictionary key errors
- `FileNotFoundError:` - Missing files
- `FAILED.*test_` - Test failures
- `AssertionError:` - Assertion failures
- `ConnectionError:` / `TimeoutError:` - Network issues

### Suggested Fixes

Each detected error includes context-aware suggestions:

**Example for ImportError:**
```json
{
  "suggestions": [
    "Install the missing package: pip install <package>",
    "Check if the module name is correct",
    "Verify the package is in your requirements"
  ]
}
```

## WebSocket Streaming

Connect to the test stream for real-time test updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/test/stream');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  switch(message.type) {
    case 'start':
      console.log('Tests starting...');
      break;
    case 'progress':
      console.log('Progress:', message.data);
      break;
    case 'complete':
      console.log('Tests complete:', message.data);
      break;
    case 'error':
      console.error('Error:', message.data);
      break;
  }
};
```

## Common Issues

### 1. Tests Not Running

**Symptom:** `POST /debug/test` returns 500 error

**Solution:**
- Check pytest is installed in the virtual environment
- Verify tests directory exists
- Check Python version compatibility
- Review pytest output for configuration errors

### 2. High Error Count

**Symptom:** `debug/status` shows many errors

**Solution:**
- Review errors with `GET /debug/errors`
- Filter by severity to prioritize critical issues
- Check context files in `.buildrunner/context/`
- Fix code issues and errors will auto-clear

### 3. WebSocket Connection Failures

**Symptom:** Cannot connect to `/test/stream`

**Solution:**
- Ensure API is running
- Check firewall settings
- Verify WebSocket support in client
- Try connecting via browser dev tools

### 4. Slow API Responses

**Symptom:** High response times in `X-Response-Time` header

**Solution:**
- Check if background test runner is consuming resources
- Review feature registry size (large features.json)
- Monitor system resources (CPU, memory)
- Consider adding pagination for large result sets

### 5. Feature Registry Corruption

**Symptom:** 500 errors on feature endpoints

**Solution:**
```bash
# Check features.json validity
python3 -c "import json; print(json.load(open('.buildrunner/features.json')))"

# Backup and regenerate if needed
cp .buildrunner/features.json .buildrunner/features.json.bak
# Manually fix JSON or restore from git
```

## Performance Monitoring

### Check Response Times

```bash
# Get response time for all endpoints
for endpoint in /health /features /metrics /debug/status; do
  echo -n "$endpoint: "
  curl -w "%{time_total}s\n" -o /dev/null -s http://localhost:8000$endpoint
done
```

### Monitor Background Processes

```bash
# Check if test runner is active
curl http://localhost:8000/test/status | jq '.is_running'

# Check error watcher status
curl http://localhost:8000/debug/status | jq '.error_count'
```

## Logging

### Enable Debug Logging

```bash
uvicorn api.main:app --log-level debug
```

### Watch API Logs in Real-Time

```bash
tail -f api.log
```

## Testing the API

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test Suite

```bash
pytest tests/test_api.py -v
pytest tests/test_api_debug.py -v
```

### Check Coverage

```bash
pytest tests/ --cov=api --cov-report=html
open htmlcov/index.html
```

## Health Check Script

Save as `health_check.sh`:

```bash
#!/bin/bash
API_URL=${1:-http://localhost:8000}

echo "=== BuildRunner API Health Check ==="
echo ""

# Basic health
echo "1. Health Status:"
curl -s $API_URL/health | jq '.status'

# System diagnostics
echo -e "\n2. System Status:"
curl -s $API_URL/debug/status | jq '{status, features_loaded, error_count, tests_running}'

# Error summary
echo -e "\n3. Error Summary:"
curl -s $API_URL/debug/errors | jq '{total_errors, by_severity}'

# Test runner
echo -e "\n4. Test Runner:"
curl -s $API_URL/test/status | jq '{is_running, interval}'

echo -e "\n=== Health Check Complete ==="
```

Usage:
```bash
chmod +x health_check.sh
./health_check.sh
./health_check.sh http://production-api.com
```

## Troubleshooting Checklist

- [ ] API is running (`curl http://localhost:8000/health`)
- [ ] Virtual environment is activated
- [ ] All dependencies installed (`pip list`)
- [ ] Features.json exists and is valid JSON
- [ ] Tests directory exists
- [ ] Python version >= 3.11
- [ ] No port conflicts (8000 in use)
- [ ] Sufficient disk space for logs and context files
- [ ] File permissions correct on `.buildrunner/`

## Getting Help

If issues persist:

1. Check logs for stack traces
2. Run health check script
3. Review error summary
4. Check system resources
5. Verify configuration files
6. Test with minimal features.json
7. Report issues with full error context

## Production Debugging

**DO NOT enable debug endpoints in production without authentication!**

For production debugging:
- Add API key authentication to debug endpoints
- Restrict debug endpoints to admin users only
- Monitor error rates with external tools
- Use structured logging (JSON format)
- Set up alerts for critical errors
- Implement rate limiting on all endpoints

## Development Tips

- Use `--reload` flag for auto-reload during development
- Enable debug logging for verbose output
- Test WebSocket connections with browser dev tools
- Use `pytest -vv` for extra verbose test output
- Run tests in watch mode: `pytest-watch`
- Profile slow endpoints with `cProfile`
