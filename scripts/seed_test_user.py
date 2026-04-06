import sys
import os
import uuid
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.queue.database import get_session, create_db_and_tables
from pipeline.queue.repository import TaskRepository
from api.models import User, Identity
from api.auth import hash_password

def seed_test_user():
    email = "test@example.com"
    password = "StrongPassword123"
    name = "Test User"
    
    print(f"Seeding test user: {email}")
    
    # Ensure tables exist
    create_db_and_tables()
    
    with get_session() as session:
        repo = TaskRepository(session)
        
        # Check if user exists
        existing_user = session.query(User).filter(User.email == email).first()
        if existing_user:
            print(f"User {email} already exists. Updating password...")
            identity = session.query(Identity).filter(Identity.user_id == existing_user.user_id, Identity.provider == "email").first()
            if identity:
                identity.hashed_password = hash_password(password)
                identity.updated_at = datetime.utcnow()
            else:
                identity = Identity(
                    user_id=existing_user.user_id,
                    provider="email",
                    provider_provider_id=email,
                    hashed_password=hash_password(password)
                )
                session.add(identity)
            session.commit()
            print("Done.")
            return

        # Create new user
        user = User(
            user_id=uuid.uuid4(),
            email=email,
            name=name,
            is_active=True,
            role="admin"
        )
        session.add(user)
        session.flush() # Get user_id
        
        identity = Identity(
            user_id=user.user_id,
            provider="email",
            provider_id=email,
            hashed_password=hash_password(password)
        )
        session.add(identity)
        session.commit()
        print(f"Successfully created user {email} with password {password}")

if __name__ == "__main__":
    seed_test_user()
