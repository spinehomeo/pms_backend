import os

IGNORE_FOLDERS = {".venv", "__pycache__", ".git"}

def print_tree(start_path, indent=""):
    items = sorted(os.listdir(start_path), key=lambda x: (not os.path.isdir(os.path.join(start_path, x)), x))
    
    for item in items:
        if item in IGNORE_FOLDERS:
            continue  # Skip ignored folders

        path = os.path.join(start_path, item)
        print(indent + "|-- " + item)

        if os.path.isdir(path):
            print_tree(path, indent + "|   ")

root = "../"  # Change this to your desired root directory
print_tree(root)
