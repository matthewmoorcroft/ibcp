# Testing Strategy for IBCP

This document explains the testing approach for the `ibcp` library and why integration tests are not necessary for API wrapper libraries.

---

## 🎯 **Testing Philosophy**

For an **API wrapper library** like `ibcp`, **unit tests with mocked responses are sufficient**. Here's why:

### **What We're Testing:**
- ✅ Your library's logic (parsing, validation, error handling)
- ✅ Data transformation (API response → Python objects)
- ✅ Retry mechanisms
- ✅ Caching behavior
- ✅ Exception handling
- ✅ Parameter validation

### **What We're NOT Testing:**
- ❌ Interactive Brokers' API itself (that's their responsibility)
- ❌ Network connectivity (not your library's concern)
- ❌ IB Gateway's behavior (external system)

---

## 📋 **Current Test Structure**

```
tests/
├── unit/                    # ✅ Core tests (YOU HAVE THESE)
│   ├── test_rest_client.py # Tests your library logic
│   ├── test_config.py       # Tests configuration
│   └── conftest.py          # Test fixtures
├── benchmarks/              # ✅ Performance tests (YOU HAVE THESE)
│   └── test_performance.py  # Measures speed
└── integration/             # ⚠️ Optional (NOT NEEDED)
    └── (empty)              # Would test against real IB Gateway
```

---

## ✅ **Why Unit Tests Are Sufficient**

### **Example: Testing `get_conid()`**

**Your Unit Test (Mocked):**
```python
def test_get_conid():
    """Test getting contract ID for a symbol."""
    # Mock the API response
    api_response = {
        "AAPL": [
            {
                "symbol": "AAPL",
                "contracts": [{"conid": 265598, "isUS": True}]
            }
        ]
    }

    with patch.object(client, "_make_request", return_value=api_response):
        conid = client.get_conid("AAPL")
        assert conid == 265598  # ✅ Tests YOUR parsing logic
```

**What This Tests:**
1. ✅ Your library correctly extracts the `conid` from the nested structure
2. ✅ Your library handles the filtering logic
3. ✅ Your library raises the right exceptions for invalid data
4. ✅ Your library applies caching correctly

**What This Doesn't Test (And That's OK!):**
- ❌ Whether IB's API actually returns this format (that's IB's problem)
- ❌ Whether the network request succeeds (not your library's concern)
- ❌ Whether IB Gateway is running (user's environment)

---

## ❌ **Why Integration Tests Are Usually Not Needed**

### **Challenges with Integration Tests for API Wrappers:**

1. **Requires External Service**
   - Need IB Gateway running (desktop app)
   - Need valid IB account credentials
   - Can't run in CI without secrets

2. **Slow & Unreliable**
   - Network latency (seconds vs milliseconds)
   - Rate limits from IB
   - Service might be down

3. **Hard to Test Edge Cases**
   - How do you test "rate limit exceeded"?
   - How do you test "invalid symbol"?
   - How do you test "network timeout"?
   - **Answer:** Mock these scenarios in unit tests!

4. **Doesn't Add Much Value**
   - If your unit tests pass, your library works
   - If IB's API changes, your users will report it
   - You can't control IB's API behavior anyway

---

## 🔄 **When You WOULD Need Integration Tests**

You'd only need integration tests if:

### **1. You're Building a Trading Bot**
```python
# Integration test for a trading bot
def test_full_trading_workflow():
    bot = TradingBot()
    bot.connect_to_ib_gateway()
    bot.place_order("AAPL", quantity=1)
    bot.wait_for_fill()
    bot.close_position()
    # ✅ Tests the entire workflow
```

### **2. You're Testing Multi-Step Workflows**
```python
# Integration test for complex workflow
def test_order_lifecycle():
    # 1. Place order
    order_id = client.submit_order(...)
    # 2. Wait for confirmation
    time.sleep(2)
    # 3. Modify order
    client.modify_order(order_id, ...)
    # 4. Cancel order
    client.cancel_order(order_id)
    # ✅ Tests interaction between multiple API calls
```

### **3. You're Validating Against Real IB Gateway**
- To catch breaking changes in IB's API
- To verify your understanding of API behavior
- **BUT:** This should be done manually, not in CI

---

## 🎯 **Recommended Testing Approach**

### **For CI (Automated):**
```yaml
✅ Unit Tests (with mocks)      → Fast, reliable, no external deps
✅ Type Checking (mypy)         → Catches type errors
✅ Security Scanning (bandit)   → Finds vulnerabilities
✅ Code Coverage (55%+)         → Ensures sufficient testing
✅ Performance Benchmarks       → Measures speed
❌ Integration Tests            → Not needed in CI
```

### **For Local Development:**
```bash
# Quick feedback loop (< 5 seconds)
$ pre-commit run --all-files

# Run all tests (< 10 seconds)
$ uv run pytest

# Manual integration test (when needed)
$ # 1. Start IB Gateway manually
$ # 2. Run: uv run pytest tests/integration/ -v
```

---

## 🛠️ **How to Do Manual Integration Testing**

If you want to test against a real IB Gateway:

### **Step 1: Start IB Gateway**
```bash
# Download and run IB Gateway from:
# https://www.interactivebrokers.com/en/index.php?f=16457
```

### **Step 2: Create a Manual Test Script**
```python
# manual_test.py
from ibcp import REST

# Point to your local IB Gateway
client = REST(base_url="https://localhost:5000")

# Test basic functionality
print("Accounts:", client.get_accounts())
print("AAPL Contract ID:", client.get_conid("AAPL"))
print("AAPL Price:", client.get_stock_last_price("AAPL"))
```

### **Step 3: Run Manually**
```bash
$ python manual_test.py
Accounts: [{'accountId': 'DU123456', ...}]
AAPL Contract ID: 265598
AAPL Price: 150.25
```

**This is better than automated integration tests because:**
- ✅ You can visually inspect results
- ✅ You can test with real market data
- ✅ You can test interactively
- ✅ No CI complexity

---

## 📊 **Current Test Coverage**

```
Module                  Coverage   Status
src/ibcp/ibcp.py        56%        ✅ Good
src/ibcp/exceptions.py  67%        ✅ Good
src/ibcp/config.py      47%        ⚠️ Could improve
Total                   55.19%     ✅ Above 50% threshold
```

### **How to Improve Coverage (If Desired):**

1. **Add tests for edge cases:**
   ```python
   def test_get_conid_with_multiple_contracts():
       # Test filtering when multiple contracts exist

   def test_get_conid_cache_hit():
       # Test LRU cache behavior

   def test_rate_limit_error_handling():
       # Test retry logic for 429 errors
   ```

2. **Add tests for configuration:**
   ```python
   def test_config_from_toml():
       # Test loading from TOML file

   def test_config_validation():
       # Test invalid config values
   ```

3. **Add tests for error scenarios:**
   ```python
   def test_connection_timeout():
       # Test timeout handling

   def test_invalid_json_response():
       # Test malformed response handling
   ```

---

## 🎓 **Best Practices for API Wrapper Testing**

### **1. Mock External Calls**
```python
✅ Good: Mock _make_request() to return data
❌ Bad:  Make real HTTP requests in tests
```

### **2. Test Your Logic, Not IB's API**
```python
✅ Good: Test that you parse {"conid": 123} correctly
❌ Bad:  Test that IB returns {"conid": 123}
```

### **3. Use Realistic Mock Data**
```python
✅ Good: Use actual API response format from IB docs
❌ Bad:  Use simplified/fake response structures
```

### **4. Test Error Handling**
```python
✅ Good: Mock 429 responses, test retry logic
✅ Good: Mock empty responses, test error messages
❌ Bad:  Only test happy path
```

### **5. Keep Tests Fast**
```python
✅ Good: < 10 seconds for full test suite
❌ Bad:  Minutes of waiting for network calls
```

---

## 📝 **Summary**

### **For IBCP Library:**

| Test Type | Status | Needed? | Reason |
|-----------|--------|---------|--------|
| Unit Tests | ✅ Have | ✅ Yes | Tests your library logic |
| Type Checking | ✅ Have | ✅ Yes | Catches type errors |
| Security Scan | ✅ Have | ✅ Yes | Finds vulnerabilities |
| Performance Tests | ✅ Have | ✅ Yes | Measures speed |
| Integration Tests | ❌ None | ❌ No | Unit tests are sufficient |

### **Key Takeaway:**

**Your current test setup is perfect for an API wrapper library!** 🎉

- ✅ 16/16 tests pass
- ✅ 55% code coverage
- ✅ Fast (< 10 seconds)
- ✅ No external dependencies
- ✅ Runs in CI

**You don't need integration tests.** If IB's API changes, your users will let you know, and you can add unit tests for the new behavior.

---

## 🔗 **Additional Resources**

- [Martin Fowler on Test Doubles](https://martinfowler.com/bliki/TestDouble.html)
- [Python Testing Best Practices](https://docs.python-guide.org/writing/tests/)
- [unittest.mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
