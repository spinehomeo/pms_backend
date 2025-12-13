# import_fix.py - UPDATED VERSION
import os
import re

def update_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        print(f"Skipping binary file: {filepath}")
        return
    
    # Remove pms_backend. prefix from imports
    updated = re.sub(r'from pms_backend\.', 'from ', content)
    updated = re.sub(r'import pms_backend\.', 'import ', updated)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(updated)
    print(f"Updated: {filepath}")

def fix_imports():
    print("Fixing imports...")
    
    # Update main.py first
    if os.path.exists('main.py'):
        update_file('main.py')
    
    # Update other .py files
    for root, dirs, files in os.walk('.'):
        # Skip virtual environment and git directories
        dirs[:] = [d for d in dirs if d not in ['.venv', '.git', '__pycache__', 'node_modules']]
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'pms_backend.' in content:
                            update_file(filepath)
                except UnicodeDecodeError:
                    print(f"Skipping non-text file: {filepath}")
                    continue
                except Exception as e:
                    print(f"Error processing {filepath}: {e}")

if __name__ == "__main__":
    fix_imports()
    print("\nDone! Don't forget to:")
    print("1. Update Procfile to: web: uvicorn main:app --host 0.0.0.0 --port $PORT")
    print("2. Check other files (alembic/env.py, tests, etc.)")