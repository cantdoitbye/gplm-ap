import asyncio
import sys
import os
from passlib.context import CryptContext

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.connection import async_session_maker
from sqlalchemy import text

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

async def main():
    email = "admin@ooumph.com"
    password = "admin123"
    
    try:
        async with async_session_maker() as session:
            result = await session.execute(text("SELECT email FROM users WHERE email = :email"), {"email": email})
            user = result.fetchone()
            
            if user:
                print(f"User '{email}' already exists!")
                return
                
            print(f"Creating user '{email}'...")
            hashed_pwd = get_password_hash(password)
            
            insert_query = text("""
                INSERT INTO users (email, hashed_password, full_name, role, is_active, created_at, updated_at)
                VALUES (:email, :hashed_password, :full_name, :role, :is_active, NOW(), NOW())
            """)
            
            await session.execute(insert_query, {
                "email": email,
                "hashed_password": hashed_pwd,
                "full_name": "Abhishek Awasthi",
                "role": "admin",
                "is_active": True
            })
            await session.commit()
            print(f"User '{email}' created successfully with password '{password}'.")
            
    except Exception as e:
        print(f"Error seeding database: {e}")
        print("Please ensure the database is running.")

if __name__ == "__main__":
    asyncio.run(main())
