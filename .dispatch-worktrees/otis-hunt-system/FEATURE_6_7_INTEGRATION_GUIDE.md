# BuildRunner 3.2 - Features 6 & 7 Integration Guide

Quick start guide for integrating Production Features and UI Authentication.

## Quick Setup

### 1. Install Dependencies

```bash
pip install psutil pyjwt
```

### 2. Initialize Health & Load Balancing

In your main API file (`api/main.py`):

```python
from api.routes.agents import init_agent_routes
from core.agents.health import AgentHealthMonitor
from core.agents.load_balancer import AgentLoadBalancer

# Define your agents
AGENT_IDS = ["agent-1", "agent-2", "agent-3"]

# Create health monitor
health_monitor = AgentHealthMonitor(AGENT_IDS, check_interval=10.0)

# Create load balancer
load_balancer = AgentLoadBalancer(AGENT_IDS, health_monitor)

# Initialize API routes
init_agent_routes(AGENT_IDS, health_monitor, load_balancer)

# In your lifespan startup:
await health_monitor.start()
```

### 3. Register Agent Routes

```python
from api.routes.agents import router as agents_router

app.include_router(agents_router, prefix="/agents")
```

### 4. Initialize Authentication

```python
from api.auth import AuthenticationManager
from pathlib import Path

# Create auth manager
auth_manager = AuthenticationManager(
    secret_key="your-super-secret-key-change-this",
    storage_path=Path(".buildrunner/auth"),
    expiration_hours=24
)
```

### 5. Add Auth Endpoints to API

```python
@app.post("/auth/login")
async def login(email: str, password: str):
    token = auth_manager.authenticate(email, password)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return token.to_dict()

@app.post("/auth/logout")
async def logout(token: str):
    auth_manager.logout(token)
    return {"status": "logged out"}

@app.post("/auth/register")
async def register(email: str, username: str, password: str):
    user = auth_manager.register_user(email, username, password)
    if not user:
        raise HTTPException(status_code=400, detail="Registration failed")
    return user.to_dict()

@app.get("/auth/verify")
async def verify_token(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="No token provided")

    token = authorization.replace("Bearer ", "")
    payload = auth_manager.jwt_manager.verify_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = auth_manager.get_user(payload["user_id"])
    return user.to_dict()
```

### 6. Set Up UI Components

In your React app (`ui/src/App.tsx`):

```tsx
import { AuthProvider, ProtectedRoute } from './components/Login';
import { NotificationProvider, Notifications } from './components/Notifications';

function App() {
  return (
    <AuthProvider>
      <NotificationProvider>
        <Notifications />
        <ProtectedRoute>
          <YourAppContent />
        </ProtectedRoute>
      </NotificationProvider>
    </AuthProvider>
  );
}
```

## Usage Examples

### Health Monitoring

```python
from core.agents.health import AgentHealthMonitor

monitor = AgentHealthMonitor(["agent-1", "agent-2"])

# Get summary
summary = monitor.get_summary()
print(f"Healthy: {summary['healthy']}, Failing: {summary['failing']}")

# Get specific agent health
health = monitor.get_health_status("agent-1")
print(f"Agent status: {health.status.value}")

# Get history
history = monitor.get_history("agent-1", limit=20)
for check in history:
    print(f"{check['timestamp']}: {check['status']}")
```

### Load Balancing

```python
from core.agents.load_balancer import AgentLoadBalancer, LoadBalancingRequest

balancer = AgentLoadBalancer(["agent-1", "agent-2", "agent-3"], health_monitor)

# Assign a request
request = LoadBalancingRequest(
    request_id="req-123",
    task_type="build",
    priority=1,
    affinity_agent_id=None  # Optional
)

decision = await balancer.assign_request(request)
print(f"Assigned to: {decision.assigned_agent_id}")

# Release request
await balancer.release_request("req-123")

# Get load info
load = balancer.get_load_summary()
print(f"Total connections: {load['total_connections']}")

# Switch strategy
from core.agents.load_balancer import LoadBalancingStrategy
balancer.set_strategy(LoadBalancingStrategy.CPU_AWARE)
```

### Authentication

```python
from api.auth import AuthenticationManager

auth = AuthenticationManager("secret_key")

# Register user
user = auth.register_user(
    email="user@example.com",
    username="testuser",
    password="secure_password",
    role=UserRole.DEVELOPER
)

# Authenticate
token = auth.authenticate("user@example.com", "secure_password")
if token:
    print(f"Token: {token.token}")

# Get user
user = auth.get_user(user.user_id)
print(f"User: {user.username}, Role: {user.role.value}")

# Update settings
auth.update_user_settings(user.user_id, {"theme": "dark"})

# Change password
success = auth.change_password(user.user_id, "old_password", "new_password")
```

### Notifications in UI

```tsx
import { useNotifications, useSuccessNotification } from './components/Notifications';

function MyComponent() {
  const { addNotification } = useNotifications();
  const showSuccess = useSuccessNotification();

  const handleAction = () => {
    showSuccess("Success!", "Operation completed successfully");
  };

  return (
    <button onClick={handleAction}>
      Show Notification
    </button>
  );
}
```

## API Examples

### Health Check

```bash
# Get health summary
curl http://localhost:8000/agents/health

# Get specific agent health
curl http://localhost:8000/agents/health/agent-1

# Trigger immediate health check
curl -X POST http://localhost:8000/agents/health/check/agent-1

# Get health history
curl http://localhost:8000/agents/health/agent-1/history?limit=20
```

### Load Balancing

```bash
# Get load summary
curl http://localhost:8000/agents/load

# Get agent load
curl http://localhost:8000/agents/load/agent-1

# Assign request
curl -X POST http://localhost:8000/agents/assign \
  -H "Content-Type: application/json" \
  -d '{"task_type": "build", "priority": 0}'

# Release request
curl -X POST http://localhost:8000/agents/release/req-id

# Change strategy
curl -X POST http://localhost:8000/agents/strategy/health_aware
```

### Failover

```bash
# Get failover candidates
curl http://localhost:8000/agents/failover/candidates

# Trigger failover
curl -X POST http://localhost:8000/agents/failover/agent-1
```

### Authentication

```bash
# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# Verify token
curl http://localhost:8000/auth/verify \
  -H "Authorization: Bearer YOUR_TOKEN"

# Logout
curl -X POST http://localhost:8000/auth/logout \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Configuration

### Health Monitor Settings

```python
monitor = AgentHealthMonitor(agent_ids, check_interval=10.0)

# Set resource limits (in percentages)
monitor.set_resource_limits(
    cpu_percent=85.0,      # Alert if CPU > 85%
    memory_percent=80.0,   # Alert if memory > 80%
    disk_percent=90.0      # Alert if disk > 90%
)
```

### Load Balancer Settings

```python
balancer = AgentLoadBalancer(agent_ids, health_monitor)

# Set agent capacity
balancer.set_agent_capacity("agent-1", max_connections=100, weight=1.5)

# Set strategy
balancer.set_strategy(LoadBalancingStrategy.HEALTH_AWARE)
```

### Authentication Settings

```python
auth = AuthenticationManager(
    secret_key="super-secret-key",
    storage_path=Path(".buildrunner/auth"),
    expiration_hours=24  # Token expires in 24 hours
)
```

## Testing

Run tests:

```bash
pytest tests/test_feature_6_7.py -v
```

Run specific test class:

```bash
pytest tests/test_feature_6_7.py::TestAgentHealthMonitor -v
pytest tests/test_feature_6_7.py::TestAuthenticationManager -v
```

Run with coverage:

```bash
pytest tests/test_feature_6_7.py --cov=core.agents --cov=api.auth
```

## Troubleshooting

### Health checks not starting

```python
# Make sure to await the start method
await health_monitor.start()

# Check if running
print(health_monitor.is_running)
```

### Token verification failing

```python
# Verify you're using correct secret key
# Ensure token hasn't expired
# Check token format: "Bearer <token>"

payload = auth.jwt_manager.verify_token(token)
if payload is None:
    print("Token is invalid or expired")
```

### Load balancing not assigning agents

```python
# Check agent availability
balancer.capacities["agent-1"].available  # Should be True

# Check agent capacity
print(balancer.get_agent_load("agent-1"))

# Try changing strategy
balancer.set_strategy(LoadBalancingStrategy.ROUND_ROBIN)
```

### Notifications not showing

```tsx
// Ensure NotificationProvider wraps your component
<NotificationProvider>
  <YourComponent />
</NotificationProvider>

// Import hook correctly
import { useNotifications } from './components/Notifications';
```

## Default Credentials

After initialization, a default admin user is created:

- **Email:** admin@buildrunner.local
- **Password:** admin
- **Role:** admin

**Important:** Change this password in production!

```python
success = auth.change_password(
    admin_user.user_id,
    "admin",  # Old password
    "new_secure_password"
)
```

## Next Steps

1. Integrate health and load balancing endpoints
2. Set up authentication with secure secret key
3. Configure UI with AuthProvider and NotificationProvider
4. Test all endpoints with provided examples
5. Deploy to production with proper configuration

## Support

For issues or questions, refer to:
- Test files: `tests/test_feature_6_7.py`
- Implementation files: `core/agents/` and `api/auth.py`
- Example usage in docstrings

---

**Version:** 3.2.0-alpha.1
**Last Updated:** November 18, 2025
