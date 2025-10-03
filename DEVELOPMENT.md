# Development Guide

## 🚀 Quick Setup

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync --all-extras

# Install pre-commit hooks (for local development)
uv run pre-commit install
```

## 🔧 Development Workflow

### **What Runs Where?**

**Local (Pre-commit) - Fast & Auto-fixing (~5-10 seconds):**
- ✅ Ruff formatting and linting (auto-fixes)
- ✅ Mypy type checking (validation only, catches errors before push)
- ✅ File checks (trailing whitespace, etc.)
- ✅ Syntax validation

**CI (GitHub Actions) - Comprehensive Validation & Testing (~3-5 minutes):**
- ✅ Type checking (mypy) - validates again
- ✅ Security scanning (bandit)
- ✅ Full test suite with coverage
- ✅ Performance benchmarks
- ✅ Documentation build

### **Why Pre-commit Didn't Catch Errors Before?**

We initially removed Mypy from pre-commit to keep it fast. However, this meant type errors only showed up in CI. **We've now added Mypy back with relaxed settings** so it catches serious type errors locally before you push, while still running fast (~5-10 seconds total).

### **Local Development (Pre-commit)**
Pre-commit hooks run automatically when you commit and will **auto-fix** issues:

```bash
# Make your changes
git add .
git commit -m "your changes"  # Pre-commit runs automatically (~5-10 seconds)

# If you need to skip pre-commit (emergency only)
git commit --no-verify -m "emergency fix"

# IMPORTANT: Run pre-commit on ALL files before pushing
# (Pre-commit only checks staged files by default)
python -m pre_commit run --all-files
```

**💡 Tip:** Before pushing to remote, always run:
```bash
python -m pre_commit run --all-files
python -m ruff format --check .
```
This ensures you won't get formatting failures in CI.

### **Manual Code Quality Checks**
Run these manually if needed:

```bash
# Format code
uv run ruff format

# Fix linting issues
uv run ruff check --fix

# Type checking
uv run mypy src/

# Run tests
uv run pytest
```

### **CI Pipeline**
CI runs **validation only** (no auto-fixing):
- ✅ Code quality checks (read-only)
- ✅ Type checking
- ✅ Security scanning
- ✅ Tests with coverage
- ✅ Documentation build
- ✅ Performance benchmarks

## 📋 Best Practices

1. **Let pre-commit fix issues locally** - Don't fight the auto-formatting
2. **Run tests before pushing** - `uv run pytest`
3. **Check CI status** - Fix any validation failures
4. **Keep commits focused** - One logical change per commit

## 🐛 Troubleshooting

### Pre-commit Issues
```bash
# Skip pre-commit for emergency commits
git commit --no-verify -m "emergency fix"

# Update pre-commit hooks
uv run pre-commit autoupdate
```

### CI Failures
- **Code quality**: Run `uv run ruff check --fix` locally
- **Type errors**: Run `uv run mypy src/` and fix annotations
- **Test failures**: Run `uv run pytest` locally to debug
