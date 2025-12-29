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

root = "./"  # Change this to your desired root directory
print_tree(root)


# import os
# import sys
# print("Current directory:", os.getcwd())
# print("Directory contents:", os.listdir('.'))
# print("Parent contents:", os.listdir('..'))



# print("=== DEBUG INFO ===")
# print("Current dir:", os.getcwd())
# print("Python path:", sys.path)
# print("Files in current dir:", os.listdir('.'))
# if 'api' in os.listdir('.'):
#     print("✓ 'api' directory exists")
# else:
#     print("✗ 'api' directory NOT found!")
# print("==================")

# # Debug for deployment
# print("=== NORTHFLANK DEBUG ===")
# print("Working directory:", os.getcwd())
# print("Python path:", sys.path)
# print("Listing current directory:", os.listdir('.'))
# print("=======================")
