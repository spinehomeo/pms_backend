# debug_main.py - Place this in the same directory as main.py
import os
import sys
import traceback

print("=" * 60)
print("DEBUG: Testing application imports")
print("=" * 60)

# Check Python version
print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")
print(f"Python path: {sys.path[:3]}...")  # First 3 entries

# Test imports step by step
test_steps = [
    ("core.config", "from core.config import settings"),
    ("api.router", "from api.router import api_router"),
    ("main app", "from main import app"),
]

failed = False

for module_name, import_stmt in test_steps:
    print(f"\n{'='*40}")
    print(f"Testing: {module_name}")
    print(f"Import: {import_stmt}")
    print('='*40)
    
    try:
        exec(import_stmt)
        print(f"✅ SUCCESS: {module_name}")
    except ImportError as e:
        print(f"❌ IMPORT ERROR: {e}")
        traceback.print_exc()
        failed = True
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        traceback.print_exc()
        failed = True

print("\n" + "=" * 60)
if failed:
    print("❌ DEBUG FAILED: Some imports failed")
    sys.exit(1)
else:
    print("✅ DEBUG PASSED: All imports successful!")
    print("=" * 60)
    
    # Test if app can be run
    try:
        from main import app
        print("\n✅ Application can be imported successfully!")
        print(f"App title: {app.title}")
        print(f"OpenAPI URL: {app.openapi_url}")
    except Exception as e:
        print(f"\n❌ App import test failed: {e}")
        traceback.print_exc()
        sys.exit(1)