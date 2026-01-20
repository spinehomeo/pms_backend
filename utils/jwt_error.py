import jwt.exceptions
print("Available JWT exceptions:")
for attr in dir(jwt.exceptions):
    if 'Error' in attr:
        print(f"  - {attr}")