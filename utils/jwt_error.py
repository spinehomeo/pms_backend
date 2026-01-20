import jwt
print("Available JWT exceptions:")
for attr in dir(jwt):
    if 'Error' in attr or 'Decode' in attr:
        print(f"  - {attr}")