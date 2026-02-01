# DateTime Best Practices - Quick Reference

## ✅ How to Use UTC Helpers

### In Your Code
```python
from utils.time import utc_now, utc_today, utc_isoformat

# Get current time (UTC)
created_at = utc_now()

# Get today's date
today = utc_today()

# Get ISO format timestamp
timestamp = utc_isoformat()
```

### Common Use Cases

#### 1. User Last Login
```python
# ✅ Correct
user.last_login = utc_today()

# ❌ Wrong
user.last_login = datetime.now().date()
```

#### 2. Timestamp Fields
```python
# ✅ Correct
session_start = utc_now()

# ❌ Wrong
session_start = datetime.now()
```

#### 3. API Response Timestamps
```python
# ✅ Correct
return {
    "data": results,
    "timestamp": utc_isoformat()
}

# ❌ Wrong
return {
    "data": results,
    "timestamp": datetime.now().isoformat()
}
```

#### 4. Database Queries
```python
# ✅ Correct
from utils.time import utc_today

appointments = session.exec(
    select(Appointment).where(
        Appointment.appointment_date >= utc_today()
    )
).all()

# ❌ Wrong (offset-naive)
appointments = session.exec(
    select(Appointment).where(
        Appointment.appointment_date >= datetime.now().date()
    )
).all()
```

---

## 🔍 Available Functions

### `utc_now()` → datetime
Returns current time as timezone-aware datetime (UTC)

```python
from utils.time import utc_now

now = utc_now()
# Returns: datetime.datetime(2026, 2, 1, 15, 30, 45, 123456, tzinfo=datetime.timezone.utc)
```

### `utc_today()` → date
Returns today's date (UTC)

```python
from utils.time import utc_today

today = utc_today()
# Returns: datetime.date(2026, 2, 1)
```

### `utc_isoformat()` → str
Returns current time as ISO 8601 string (UTC)

```python
from utils.time import utc_isoformat

timestamp = utc_isoformat()
# Returns: '2026-02-01T15:30:45.123456+00:00'
```

---

## ⚠️ Common Mistakes to Avoid

### ❌ Don't Use Plain datetime.now()
```python
# This creates offset-naive datetime - CAN CAUSE ERRORS
created_at = datetime.now()
```

### ❌ Don't Mix aware and naive
```python
# This will raise TypeError when comparing
if datetime.now() > aware_datetime:  # ❌ ERROR!
    pass
```

### ❌ Don't Forget timezone.utc in direct calls
```python
# If you must use datetime directly (not recommended):
# ✅ Correct
now = datetime.now(timezone.utc)

# ❌ Wrong
now = datetime.now()
```

---

## 🎯 Rule of Thumb

> **Always use helper functions from `utils.time`**

If you need:
- Current time → use `utc_now()`
- Today's date → use `utc_today()`
- Timestamp string → use `utc_isoformat()`

This ensures consistency and eliminates timezone issues.

---

## 📝 Migration Guide for New Code

### Before (Old Way)
```python
from datetime import datetime, timezone

user.created_at = datetime.now(timezone.utc)
user.last_login = datetime.now(timezone.utc).date()
return {"timestamp": datetime.now(timezone.utc).isoformat()}
```

### After (New Way)
```python
from utils.time import utc_now, utc_today, utc_isoformat

user.created_at = utc_now()
user.last_login = utc_today()
return {"timestamp": utc_isoformat()}
```

---

## 🧪 Testing

The helper functions are easily testable:

```python
from unittest.mock import patch
from utils.time import utc_now
from datetime import datetime, timezone

def test_something():
    # Mock the time
    mock_time = datetime(2026, 2, 1, 12, 0, 0, tzinfo=timezone.utc)
    with patch('utils.time.utc_now', return_value=mock_time):
        # Test code here
        assert utc_now() == mock_time
```

---

## 📚 References

- **File**: `utils/time.py` - Contains all helper functions
- **Summary**: `docs/DATETIME_FIXES_SUMMARY.md` - Full implementation details
- **Imports**: Use `from utils.time import utc_now, utc_today, utc_isoformat`

---

**Last Updated**: February 1, 2026  
**Status**: Ready for Production  
**Recommended**: Use in all new datetime code
