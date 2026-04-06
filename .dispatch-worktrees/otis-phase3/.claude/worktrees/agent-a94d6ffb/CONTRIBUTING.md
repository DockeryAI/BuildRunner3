# Contributing to BuildRunner 3.0

Thank you for your interest in contributing!

## Development Setup

```bash
git clone https://github.com/buildrunner/buildrunner.git
cd buildrunner
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Code Standards

- **Formatting**: Black (line length 100)
- **Linting**: Ruff
- **Type Checking**: mypy
- **Testing**: pytest (85%+ coverage required)
- **Security**: Bandit scans

## Pull Request Process

1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes and add tests
3. Run quality checks: `black . && ruff check . && mypy . && pytest`
4. Commit: `git commit -m "feat: your feature description"`
5. Push and create PR
6. Wait for CI/CD checks to pass
7. Request review

## Commit Message Format

```
<type>: <description>

Types: feat, fix, docs, style, refactor, test, chore
```

## Adding New Features

1. Update `.buildrunner/features.json`
2. Add tests in `tests/`
3. Add documentation in `docs/`
4. Update README if needed

## Questions?

- Discord: https://discord.gg/buildrunner
- Issues: https://github.com/buildrunner/buildrunner/issues
