import sys
import os
sys.path.append(os.getcwd())

from pipeline.queue.database import get_session
from pipeline.queue.repository import TaskRepository
from api.auth import hash_password

def main():
    email = "test@example.com"
    password = "TestPassword123"
    name = "Test User"

    try:
        with get_session() as session:
            repo = TaskRepository(session)
            existing = repo.get_user_by_email(email)
            if existing:
                print(f"User {email} already exists.")
            else:
                # Password must be at least 12 chars, with upper, lower, and digit
                hashed = hash_password(password)
                user = repo.create_user_with_password(email, name, hashed, role="internal")
                print(f"User {email} created successfully.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
