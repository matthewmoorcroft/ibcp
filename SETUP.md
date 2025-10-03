# 🚀 Quick Setup Guide

## Problem You Were Having

**Pre-commit hooks were NOT installed locally**, so they weren't running when you committed code. This meant:
- ❌ Code quality issues reached CI instead of being caught locally
- ❌ CI was doing the formatting work (slow, inefficient)
- ❌ You had to wait for CI to see formatting issues

## Solution - One-Time Setup

Run this **once** to install pre-commit hooks:

```powershell
# Navigate to project directory
cd C:\Users\matth\Documents\Projects\ibcp

# Install pre-commit hooks (one-time setup)
python -m pre_commit install

# Or if you have uv working:
# uv run pre-commit install
```

## ✅ Verify It's Working

```powershell
# Check if hooks are installed
Test-Path .git\hooks\pre-commit
# Should output: True

# Test the hooks
python -m pre_commit run --all-files
```

## 📝 Now Your Workflow Will Be:

```powershell
# 1. Make your changes
code src/ibcp/ibcp.py

# 2. Stage and commit
git add .
git commit -m "feat: your changes"

# Pre-commit will automatically:
# ✅ Format your code with Ruff (~1 second)
# ✅ Fix trailing whitespace
# ✅ Check syntax
# ✅ All in 2-5 seconds!

# 3. Push
git push origin feature/quick-wins

# CI will then validate:
# ✅ Type checking
# ✅ Security scan
# ✅ Tests
# ✅ All the heavy stuff
```

## 🔧 What Changed

### Before (Broken):
```
You → Commit → Push → CI does everything → Wait 5 minutes → Failures
```

### After (Fixed):
```
You → Commit → Pre-commit fixes locally (5 sec) → Push → CI validates → Success!
```

## ⚡ Quick Commands Reference

```powershell
# Install hooks (one-time)
python -m pre_commit install

# Run hooks manually on all files
python -m pre_commit run --all-files

# Run specific tool manually
python -m ruff check --fix src/
python -m ruff format src/

# Skip pre-commit for emergency commits only
git commit --no-verify -m "emergency"

# Run tests locally before pushing
python -m pytest
```

## 🎯 What Runs Where Now

| Check | Local (Pre-commit) | CI (GitHub Actions) |
|-------|-------------------|---------------------|
| **Ruff Format** | ✅ Auto-fix | ✅ Validate |
| **Ruff Lint** | ✅ Auto-fix | ✅ Validate |
| **File cleanup** | ✅ Auto-fix | ❌ Not needed |
| **Mypy types** | ❌ Too slow | ✅ Validate |
| **Bandit security** | ❌ Too slow | ✅ Validate |
| **Pytest tests** | ⚠️ Manual | ✅ Full suite |

## 🆘 Troubleshooting

### "uv not found"
```powershell
# Use python directly instead
python -m pre_commit install
python -m ruff check --fix src/
```

### "Pre-commit is slow"
```powershell
# Skip it if needed
git commit --no-verify -m "your message"
```

### "Want to run tests before pushing"
```powershell
# Run tests manually
python -m pytest
```

## ✨ You're All Set!

Pre-commit is now configured to:
- Run fast (2-5 seconds)
- Auto-fix formatting issues
- Catch syntax errors
- Keep CI focused on validation

Just remember to run **`python -m pre_commit install`** once!
