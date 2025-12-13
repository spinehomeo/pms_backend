import os
import shutil


def delete_pycache_folders(root_folder: str):
    # Walk through all directories and subdirectories
    for dirpath, dirnames, filenames in os.walk(root_folder):
        for dirname in dirnames:
            # Check if the directory name is __pycache__
            if dirname == '__pycache__':
                pycache_path = os.path.join(dirpath, dirname)
                print(f"Deleting: {pycache_path}")
                # Remove the entire __pycache__ folder
                shutil.rmtree(pycache_path)


if __name__ == "__main__":
    # root_directory = input("Enter the root directory path: ")
    root_directory = "./"
    delete_pycache_folders(root_directory)
    print("All __pycache__ folders have been deleted.")
    
    


# del /s /q *.pyc
# del /s /q __pycache__
