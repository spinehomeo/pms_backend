import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app

print(f"{'METHOD':<10} {'PATH':<45} TAGS")
print("-" * 90)

for route in app.routes:
    if hasattr(route, "methods"):
        methods = ",".join(sorted(route.methods))
        tags = getattr(route, "tags", None)
        tags_str = ", ".join(tags) if tags else "-"
        print(f"{methods:<10} {route.path:<45} {tags_str}")
