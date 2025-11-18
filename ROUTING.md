# Model Routing Guide

**BuildRunner v3.1** - Intelligent Model Selection and Cost Optimization

**Status:** ⚠️ **Beta** - Core functionality tested, AI integration optional

---

## Overview

BuildRunner's model routing system automatically selects the optimal AI model for each task based on complexity analysis, balancing quality, cost, and latency.

**Key Features:**
- ✅ Automatic complexity estimation (heuristic-based)
- ✅ Multi-model support (Haiku, Sonnet, Opus)
- ⚠️ Cost tracking interface (persistence layer in development)
- ⚠️ Fallback handling (strategies defined, needs testing)
- ⚠️ AI-powered estimation (optional, requires API key)

---

## Quick Start

### Estimate Task Complexity

```bash
# Estimate from description
br routing estimate "Add user authentication system"

# Include files for context
br routing estimate "Refactor database layer" \
  --file src/database.py \
  --file src/models.py
```

### Select Optimal Model

```bash
# Auto-select based on complexity
br routing select "Fix critical production bug"

# With cost limit
br routing select "Add feature X" --cost-limit 0.05

# Override model selection
br routing select "Simple task" --model haiku
```

### Track Costs

```bash
# View cost summary
br routing costs

# Specific time period
br routing costs --period week

# Export to CSV
br routing costs --period month --export costs.csv
```

### List Available Models

```bash
# Show all models
br routing models

# Only available models
br routing models --available
```

---

## Complexity Estimation

### Complexity Levels

BuildRunner classifies tasks into four complexity levels:

| Level | Score Range | Typical Tasks | Recommended Model |
|-------|-------------|---------------|-------------------|
| **Simple** | 0-25 | Bug fixes, documentation, small refactors | Haiku |
| **Moderate** | 26-60 | New features, medium refactors, integrations | Sonnet |
| **Complex** | 61-85 | Architecture changes, complex algorithms, major features | Sonnet/Opus |
| **Critical** | 86-100 | Production bugs, security issues, complete rewrites | Opus |

### Complexity Factors

The estimator analyzes multiple factors:

**1. Task Description Analysis**
- Keywords (implement, refactor, optimize, critical, etc.)
- Technical terms (API, database, authentication, etc.)
- Scope indicators (all, entire, complete, etc.)

**2. File Count**
- 1-2 files: Low complexity bonus
- 3-5 files: Moderate complexity
- 6-10 files: High complexity
- 11+ files: Very high complexity

**3. Task Type**
- `bug_fix`: -10 points (usually simpler)
- `new_feature`: +15 points
- `refactor`: +10 points
- `optimization`: +5 points
- `security`: +20 points (critical)

**4. Domain Complexity**
- Security-related: +20 points
- Performance-critical: +15 points
- Database changes: +10 points
- API changes: +10 points

### Example Estimations

**Simple Task:**
```bash
$ br routing estimate "Fix typo in README.md"

Complexity Analysis:
  Level: SIMPLE
  Score: 5.0/100
  Task Type: bug_fix
  Recommended Model: haiku
  Estimated Tokens: 500
```

**Moderate Task:**
```bash
$ br routing estimate "Add user profile page" --file frontend/profile.tsx

Complexity Analysis:
  Level: MODERATE
  Score: 45.0/100
  Task Type: new_feature
  Recommended Model: sonnet
  Estimated Tokens: 2,000

Reasons:
  • Contains 2 complexity keywords
  • New feature task
  • Single file modification
```

**Critical Task:**
```bash
$ br routing estimate "Fix critical SQL injection vulnerability in auth system"

Complexity Analysis:
  Level: CRITICAL
  Score: 95.0/100
  Task Type: security
  Recommended Model: opus
  Estimated Tokens: 4,000

Reasons:
  • Contains 4 complexity keywords (critical, SQL, injection, auth)
  • Security-related task
  • Critical priority
```

---

## Model Selection

### Available Models

BuildRunner supports Anthropic's Claude models:

| Model | Tier | Context | Max Output | Input Cost | Output Cost | Latency | Best For |
|-------|------|---------|------------|------------|-------------|---------|----------|
| **Haiku** | Fast | 200K | 4K | $0.25/1M | $1.25/1M | ~500ms | Simple tasks, quick iterations |
| **Sonnet** | Balanced | 200K | 8K | $3.00/1M | $15.00/1M | ~1000ms | Most development tasks |
| **Opus** | Advanced | 200K | 8K | $15.00/1M | $75.00/1M | ~2000ms | Complex architecture, critical bugs |

### Selection Logic

The model selector chooses based on:

**1. Complexity Level**
- Simple (0-25): Haiku
- Moderate (26-60): Sonnet
- Complex (61-85): Sonnet
- Critical (86-100): Opus

**2. Cost Constraints**
```bash
# Only use models within budget
br routing select "Task" --cost-limit 0.01  # Forces Haiku
```

**3. Manual Override**
```bash
# Force specific model
br routing select "Task" --model opus
```

**4. Fallback Preferences**
- Primary fails → Try next tier down
- All models exhausted → Return error

### Selection Examples

**Auto-Selection:**
```bash
$ br routing select "Implement OAuth2 authentication"

Selected Model: SONNET
  Reason: Moderate complexity task - balanced model
  Estimated Cost: $0.012000

Model Details:
  Provider: anthropic
  Tier: balanced
  Context Window: 200,000 tokens
  Max Output: 8,192 tokens
  Latency: ~1000ms
```

**With Cost Limit:**
```bash
$ br routing select "Complex refactor" --cost-limit 0.005

Selected Model: HAIKU
  Reason: Cost constraint ($0.005) - using fastest model
  Estimated Cost: $0.004500

Note: Task complexity suggests Sonnet, but cost limit requires Haiku
```

**Manual Override:**
```bash
$ br routing select "Simple task" --model opus

Selected Model: OPUS
  Reason: Manual override
  Estimated Cost: $0.015000

Warning: Task complexity is SIMPLE - Haiku recommended for cost savings
```

---

## Cost Tracking

### Cost Calculation

Costs are calculated based on:
- Input tokens × Input cost per million
- Output tokens × Output cost per million

**Example:**
```
Task with 1,000 input tokens, 500 output tokens on Sonnet:
Input cost:  1,000 × $3.00/1M = $0.003000
Output cost: 500 × $15.00/1M = $0.007500
Total cost:  $0.010500
```

### Viewing Costs

**Summary:**
```bash
$ br routing costs

Cost Summary - ALL TIME

Overall:
  Total Requests: 127
  Total Cost: $5.4320
  Total Tokens: 345,000
  Avg Cost/Request: $0.042756
  Avg Tokens/Request: 2,717

Cost by Model:
  sonnet: $3.2100 (95 requests)
  opus: $2.0900 (25 requests)
  haiku: $0.1320 (7 requests)

Cost by Task Type:
  new_feature: $2.1500
  refactor: $1.8900
  bug_fix: $0.9850
  optimization: $0.4070

Most Expensive Model: opus
Most Used Model: sonnet
```

**Time Periods:**
```bash
# Last hour
br routing costs --period hour

# Last day
br routing costs --period day

# Last week
br routing costs --period week

# Last month
br routing costs --period month
```

**Export to CSV:**
```bash
br routing costs --period week --export costs.csv
```

### Cost Budgets

While BuildRunner doesn't enforce budgets automatically, you can track and manually limit costs:

```bash
# Check current month cost
br routing costs --period month

# If over budget, use cheaper models
br routing select "Task" --cost-limit 0.01
```

---

## Fallback Handling

### Fallback Strategy

When a request fails, BuildRunner automatically retries with fallback models:

**Retry Chain:**
1. Try primary model (Opus/Sonnet/Haiku)
2. If fails → Try Sonnet (if not primary)
3. If fails → Try Haiku
4. If all fail → Return error

**Retry Configuration:**
- Max retries: 3 per model
- Backoff: Exponential (1s, 2s, 4s)
- Timeout: 30s per request

### Failure Types

The fallback handler detects and handles:

**1. Rate Limit (429)**
- Wait and retry with exponential backoff
- Switch to alternative model if persistent

**2. Timeout**
- Retry with same model
- Switch to faster model if persistent

**3. Server Error (5xx)**
- Retry with exponential backoff
- Switch to alternative model after 3 failures

**4. Invalid Request (400)**
- No retry (fix request)
- Report error immediately

**5. Authentication Error (401/403)**
- No retry (fix credentials)
- Report error immediately

**6. Context Length Exceeded**
- Retry with model with larger context
- Or truncate input and retry

### Example Fallback

```python
from core.routing import FallbackHandler, ModelSelector

handler = FallbackHandler()
selector = ModelSelector()

# Try primary model
try:
    result = execute_with_model("opus", prompt)
except Exception as e:
    # Automatic fallback
    fallback_result = handler.handle_failure(
        error=e,
        prompt=prompt,
        attempted_model="opus",
        attempt=1,
    )

    if fallback_result.should_retry:
        # Retry with fallback model
        result = execute_with_model(
            fallback_result.model,
            prompt,
        )
```

---

## CLI Commands Reference

### `br routing estimate`

Estimate task complexity.

**Usage:**
```bash
br routing estimate <description> [OPTIONS]
```

**Options:**
- `--file, -f` - Files involved (can specify multiple)

**Output:**
- Complexity level and score
- Task type classification
- Recommended model
- Estimated tokens
- Top complexity reasons
- Complexity factors breakdown

**Example:**
```bash
br routing estimate "Implement caching layer" \
  --file src/cache.py \
  --file src/redis_client.py
```

### `br routing select`

Select optimal model for task.

**Usage:**
```bash
br routing select <description> [OPTIONS]
```

**Options:**
- `--file, -f` - Files involved
- `--cost-limit` - Maximum cost allowed
- `--model` - Override model selection (haiku/sonnet/opus)

**Output:**
- Selected model with justification
- Estimated cost
- Model specifications
- Alternative models

**Example:**
```bash
br routing select "Build API endpoint" --cost-limit 0.02
```

### `br routing costs`

Show cost summary.

**Usage:**
```bash
br routing costs [OPTIONS]
```

**Options:**
- `--period, -p` - Time period (hour/day/week/month/all)
- `--export` - Export to CSV file

**Output:**
- Total requests, cost, tokens
- Average cost per request
- Cost breakdown by model
- Cost breakdown by task type
- Most expensive/used models

**Example:**
```bash
br routing costs --period week --export weekly-costs.csv
```

### `br routing models`

List available models.

**Usage:**
```bash
br routing models [OPTIONS]
```

**Options:**
- `--available` - Only show currently available models

**Output:**
- Model name and tier
- Context window and max output
- Input/output costs
- Average latency
- Availability status

**Example:**
```bash
br routing models --available
```

---

## Programmatic Usage

### Basic Example

```python
from core.routing import ComplexityEstimator, ModelSelector, CostTracker
from pathlib import Path

# Estimate complexity
estimator = ComplexityEstimator()
complexity = estimator.estimate(
    task_description="Add user authentication",
    files=[Path("src/auth.py"), Path("src/models.py")],
)

print(f"Complexity: {complexity.level} ({complexity.score}/100)")
print(f"Recommended: {complexity.recommended_model}")

# Select model
selector = ModelSelector()
selection = selector.select(complexity)

print(f"Selected: {selection.model.name}")
print(f"Estimated cost: ${selection.estimated_cost:.6f}")

# Track cost
tracker = CostTracker()
tracker.track_request(
    model=selection.model.name,
    input_tokens=1000,
    output_tokens=500,
    task_type="new_feature",
    success=True,
)

# Get summary
summary = tracker.get_summary(period="day")
print(f"Total cost today: ${summary.total_cost:.4f}")
```

### Advanced Complexity Analysis

```python
from core.routing import ComplexityEstimator
from pathlib import Path

estimator = ComplexityEstimator()

# Analyze task
task_desc = """
Implement a caching layer with Redis for the API endpoints.
Requirements:
- Cache GET requests for 5 minutes
- Invalidate cache on POST/PUT/DELETE
- Add cache hit/miss metrics
- Handle connection failures gracefully
"""

files = [
    Path("src/api/cache.py"),
    Path("src/api/endpoints.py"),
    Path("src/config.py"),
    Path("tests/test_cache.py"),
]

complexity = estimator.estimate(task_desc, files)

# Detailed analysis
print(f"Level: {complexity.level}")
print(f"Score: {complexity.score}/100")
print(f"Task Type: {complexity.task_type}")
print(f"\nTop Reasons:")
for reason in complexity.reasons[:5]:
    print(f"  • {reason}")

print(f"\nComplexity Factors:")
print(f"  Architecture: {complexity.factors.get('architecture', 0)}")
print(f"  Security: {complexity.factors.get('security', 0)}")
print(f"  Performance: {complexity.factors.get('performance', 0)}")
print(f"  Integration: {complexity.factors.get('integration', 0)}")
```

### Cost-Aware Model Selection

```python
from core.routing import ComplexityEstimator, ModelSelector

estimator = ComplexityEstimator()
selector = ModelSelector()

# Daily budget: $10
daily_budget = 10.00
current_spent = 7.50
remaining = daily_budget - current_spent

# Select model within remaining budget
complexity = estimator.estimate("Add new feature", [])
max_cost_per_request = remaining / 10  # Assuming 10 more requests today

selection = selector.select(
    complexity,
    cost_limit=max_cost_per_request,
)

if selection.estimated_cost > max_cost_per_request:
    print(f"Warning: Estimated cost ${selection.estimated_cost:.4f} exceeds limit")
    # Use cheaper model
    selection = selector.select_model_by_name("haiku")
```

### Fallback Example

```python
from core.routing import FallbackHandler

handler = FallbackHandler()

def execute_task(prompt: str):
    models = ["opus", "sonnet", "haiku"]

    for model in models:
        for attempt in range(3):
            try:
                result = call_model(model, prompt)
                return result
            except Exception as e:
                fallback = handler.handle_failure(
                    error=e,
                    prompt=prompt,
                    attempted_model=model,
                    attempt=attempt + 1,
                )

                if not fallback.should_retry:
                    # Non-retryable error
                    raise e

                if fallback.model != model:
                    # Switch to different model
                    print(f"Switching to {fallback.model}")
                    break

                # Retry with backoff
                time.sleep(fallback.backoff_seconds)

    raise Exception("All models failed")
```

---

## Best Practices

### Complexity Estimation

1. **Include Relevant Files**
   ```bash
   # More context = better estimation
   br routing estimate "Refactor auth" \
     --file src/auth.py \
     --file src/models.py \
     --file tests/test_auth.py
   ```

2. **Be Specific in Descriptions**
   ```bash
   # Good
   br routing estimate "Fix SQL injection in login endpoint"

   # Less helpful
   br routing estimate "Fix bug"
   ```

3. **Understand the Estimator**
   - ⚠️ Uses heuristic-based analysis (AI mode optional, not yet integrated)
   - Manual overrides available when needed
   - Estimation improves with clear task descriptions

### Model Selection

1. **Use Auto-Selection**
   - Let the system choose based on complexity
   - Only override when you have specific requirements

2. **Set Cost Limits Wisely**
   ```bash
   # For experimentation
   br routing select "Task" --cost-limit 0.01  # Use Haiku

   # For production
   br routing select "Task" --cost-limit 0.10  # Allow Opus if needed
   ```

3. **Review Cost Regularly**
   ```bash
   # Daily review
   br routing costs --period day
   ```

### Cost Optimization

1. **Batch Similar Tasks**
   - Group related tasks to reuse context
   - Reduces total token count

2. **Use Appropriate Models**
   - Haiku for simple tasks (70% cost savings vs Sonnet)
   - Sonnet for most tasks (80% cost savings vs Opus)
   - Opus only for critical/complex tasks

3. **Monitor Trends**
   ```bash
   # Weekly cost analysis
   br routing costs --period week --export costs.csv
   # Analyze in spreadsheet for patterns
   ```

4. **Set Budget Alerts**
   ```python
   # In your automation
   summary = tracker.get_summary(period="day")
   if summary.total_cost > 10.00:
       send_alert("Daily budget exceeded!")
   ```

---

## Troubleshooting

### Incorrect Complexity Estimation

**Symptom:** Task estimated as simple but requires complex reasoning

**Solutions:**
1. Include more files in estimation
2. Add more detail to task description
3. Manually override model selection
4. Report estimation error for training

### Cost Higher Than Expected

**Symptom:** Monthly costs exceed budget

**Solutions:**
1. Review cost breakdown
   ```bash
   br routing costs --period month
   ```
2. Check for inefficient tasks (many retries, large outputs)
3. Use cost limits for non-critical tasks
4. Consider using Haiku more frequently

### Model Selection Not Optimal

**Symptom:** Wrong model chosen for task

**Solutions:**
1. Verify complexity estimation is accurate
2. Set explicit cost limits if needed
3. Use manual override for edge cases
4. Review and adjust complexity keywords

### Fallback Not Working

**Symptom:** Requests fail without trying fallback models

**Solutions:**
1. Check error type (some errors don't support fallback)
2. Verify all models are configured correctly
3. Check network connectivity
4. Review fallback handler logs

---

## Advanced Topics

### Custom Complexity Rules

```python
from core.routing import ComplexityEstimator

class CustomEstimator(ComplexityEstimator):
    def estimate(self, task_description, files=None):
        # Get base complexity
        complexity = super().estimate(task_description, files)

        # Custom rules
        if "machine learning" in task_description.lower():
            complexity.score += 30  # ML tasks are complex
            complexity.reasons.insert(0, "Machine learning task")

        if "frontend" in task_description.lower():
            complexity.score -= 10  # Frontend tasks often simpler
            complexity.reasons.insert(0, "Frontend task")

        # Recalculate level
        complexity.level = self._calculate_level(complexity.score)

        return complexity
```

### Cost Prediction

```python
from core.routing import CostTracker, ComplexityEstimator, ModelSelector

tracker = CostTracker()
estimator = ComplexityEstimator()
selector = ModelSelector()

# Predict cost for upcoming sprint
tasks = [
    "Add user profile page",
    "Implement notifications",
    "Fix login bug",
    "Refactor database layer",
    "Add API documentation",
]

total_estimated_cost = 0
for task in tasks:
    complexity = estimator.estimate(task)
    selection = selector.select(complexity)
    total_estimated_cost += selection.estimated_cost

print(f"Sprint estimated cost: ${total_estimated_cost:.4f}")
```

### Model Performance Tracking

```python
from core.routing import CostTracker

tracker = CostTracker()

# Track by model
summary = tracker.get_summary(period="week")

for model_name, cost in summary.cost_by_model.items():
    requests = summary.requests_by_model.get(model_name, 0)
    avg_cost = cost / requests if requests > 0 else 0

    print(f"{model_name}:")
    print(f"  Requests: {requests}")
    print(f"  Total Cost: ${cost:.4f}")
    print(f"  Avg Cost: ${avg_cost:.6f}")
```

---

## Integration Examples

### With Task Orchestrator

```python
from core.orchestrator import Orchestrator
from core.routing import ComplexityEstimator, ModelSelector, CostTracker

class SmartOrchestrator(Orchestrator):
    def __init__(self):
        super().__init__()
        self.estimator = ComplexityEstimator()
        self.selector = ModelSelector()
        self.tracker = CostTracker()

    def execute_task(self, task):
        # Estimate complexity
        complexity = self.estimator.estimate(
            task.description,
            task.files,
        )

        # Select model
        selection = self.selector.select(complexity)

        # Execute with selected model
        result = self.call_model(
            selection.model.name,
            task.prompt,
        )

        # Track cost
        self.tracker.track_request(
            model=selection.model.name,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            task_type=complexity.task_type,
            success=result.success,
        )

        return result
```

### With Quality Gates

```python
from core.routing import CostTracker
from core.code_quality import QualityGate

# Define budget quality gate
cost_tracker = CostTracker()

def check_budget_gate():
    summary = cost_tracker.get_summary(period="day")
    daily_budget = 10.00

    if summary.total_cost > daily_budget:
        return False, f"Daily budget exceeded: ${summary.total_cost:.4f} > ${daily_budget}"

    return True, "Within budget"

# Use in quality gate
passed, message = check_budget_gate()
if not passed:
    print(f"Budget gate failed: {message}")
    # Switch to Haiku-only mode
```

---

## FAQ

**Q: How accurate is the complexity estimator?**

A: The estimator uses heuristic-based analysis of task descriptions, file counts, and keywords. Accuracy varies depending on task description clarity. AI-powered complexity estimation is available but optional (requires Claude API key). Manual overrides are supported for edge cases.

**Q: Can I add custom models?**

A: Not currently. BuildRunner supports Anthropic Claude models (Haiku, Sonnet, Opus). Support for custom models is planned for a future release.

**Q: How are costs calculated?**

A: Costs are calculated based on Anthropic's pricing: input tokens × input rate + output tokens × output rate. Rates are current as of v3.1 release.

**Q: Can I set a hard cost limit?**

A: You can set per-request cost limits with `--cost-limit`, but there's no automatic budget enforcement. Use cost tracking and monitoring to stay within budget.

**Q: What happens if all models fail?**

A: After trying all fallback models with exponential backoff, the request fails and returns an error. Check error logs for details.

**Q: Can I export cost data for accounting?**

A: Yes! Use `br routing costs --export costs.csv` to export detailed cost data.

---

## See Also

- [PARALLEL.md](PARALLEL.md) - Parallel orchestration
- [TELEMETRY.md](TELEMETRY.md) - Monitoring and metrics
- [SECURITY.md](SECURITY.md) - Security safeguards
- [README.md](README.md) - Main documentation

---

*BuildRunner v3.1 - Model Routing System*
