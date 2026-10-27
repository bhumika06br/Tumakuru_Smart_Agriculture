
import re
import sqlite3

from argon2 import PasswordHasher
from argon2.exceptions import (
    VerifyMismatchError,
    VerificationError,
    InvalidHashError,
)

from src.database import get_connection, initialize_database


password_hasher = PasswordHasher()


def validate_password(username, password):
    if len(password) < 8:
        return False, "Password must contain at least 8 characters."

    if len(password) > 128:
        return False, "Password must not exceed 128 characters."

    if not re.search(r"[A-Z]", password):
        return False, "Password must contain an uppercase letter."

    if not re.search(r"[a-z]", password):
        return False, "Password must contain a lowercase letter."

    if not re.search(r"[0-9]", password):
        return False, "Password must contain a number."

    if not re.search(r"[^A-Za-z0-9\s]", password):
        return False, "Password must contain a special character."

    if any(character.isspace() for character in password):
        return False, "Password must not contain spaces."

    if username.strip().lower() in password.lower():
        return False, "Password must not contain your username."

    common_passwords = {
        "password@1234",
        "password123!",
        "admin@123456",
        "welcome@1234",
        "qwerty@12345",
        "123456789@ab",
    }

    if password.lower() in common_passwords:
        return False, "This password is too common. Choose another."

    return True, "Strong password."


def register_farmer(username, password):
    initialize_database()

    username = username.strip()

    if not 3 <= len(username) <= 30:
        return False, "Username must contain 3 to 30 characters."

    if not all(
        c.isascii() and (c.isalnum() or c == "_")
        for c in username
    ):
        return False, (
            "Username may contain only English letters, "
            "numbers and underscores."
        )

    valid, message = validate_password(username, password)

    if not valid:
        return False, message

    password_hash = password_hasher.hash(password)

    try:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO farmers (username, password_hash)
                VALUES (?, ?)
                """,
                (username, password_hash),
            )

        return True, "Account created successfully!"

    except sqlite3.IntegrityError:
        return False, "This username is already registered."


def login_farmer(username, password):
    initialize_database()

    username = username.strip()

    with get_connection() as connection:
        farmer = connection.execute(
            """
            SELECT farmer_id, username, password_hash
            FROM farmers
            WHERE username = ?
            """,
            (username,),
        ).fetchone()

    if farmer is None:
        return None

    try:
        password_hasher.verify(
            farmer["password_hash"],
            password,
        )

    except (
        VerifyMismatchError,
        VerificationError,
        InvalidHashError,
    ):
        return None

    return {
        "farmer_id": farmer["farmer_id"],
        "username": farmer["username"],
    }
