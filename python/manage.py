"""Emergency administration from the server console.

    docker compose exec python-app python -m python.manage list-users
    docker compose exec python-app python -m python.manage reset-password admin
    docker compose exec python-app python -m python.manage disable-2fa admin
    docker compose exec python-app python -m python.manage create-admin <username>
"""
import getpass
import sys

import python.db as db
from python.pwd import hash_password


def _ask_password() -> str:
    while True:
        password = getpass.getpass("New password (min 8 chars): ")
        if len(password) >= 8 and password == getpass.getpass("Repeat: "):
            return password
        print("Passwords do not match or are too short.")


def main(argv: list[str]) -> int:
    db.create_table()
    if len(argv) < 1 or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    command, args = argv[0], argv[1:]
    if command == "list-users":
        for user in db.list_users():
            print(f"{user['id']:>3}  {user['username']:<20} {user['role']:<7} 2FA={'on' if user['totp_enabled'] else 'off'}")
        return 0

    if not args:
        print("Username is required.")
        return 1
    username = args[0]

    if command == "create-admin":
        user = db.create_user(username, hash_password(_ask_password()), "admin")
        print(f"Created admin '{user['username']}'.")
        return 0

    user = db.get_user_by_username(username)
    if not user:
        print(f"User '{username}' not found.")
        return 1

    if command == "reset-password":
        db.update_user(user["id"], password_hash=hash_password(_ask_password()))
        db.remove_all_tokens_except(None, user["id"])
        print("Password changed, all sessions of this user were revoked.")
    elif command == "disable-2fa":
        db.update_user(user["id"], totp_enabled=0, totp_secret=None, totp_last_step=0)
        print("2FA disabled.")
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
