
import pwinput

from src.auth import register_farmer, login_farmer


print("=== Farmer Registration ===")

username = input("Choose username: ")
password = pwinput.pwinput(
    prompt="Choose password: ",
    mask="•"
)

success, message = register_farmer(username, password)
print(message)


print("\n=== Farmer Login ===")

login_username = input("Username: ")
login_password = pwinput.pwinput(
    prompt="Password: ",
    mask="•"
)

farmer = login_farmer(login_username, login_password)

if farmer:
    print("Login successful!")
    print("Farmer ID:", farmer["farmer_id"])
    print("Username:", farmer["username"])
else:
    print("Invalid username or password.")
