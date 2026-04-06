"""
Seed Script
────────────
Populates the database with demo users and transactions.
Run with: python scripts/seed.py

Demo Users Created:
  admin@finance.com    / Admin@123    (ADMIN role)
  analyst@finance.com  / Analyst@123  (ANALYST role)
  viewer@finance.com   / Viewer@123   (VIEWER role)
"""

import sys
import os
import random
from datetime import date, timedelta
from decimal import Decimal

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.core.permissions import Role
from app.core.security import get_password_hash
from app.models.user import User
from app.models.transaction import Transaction, TransactionType

INCOME_CATEGORIES = ["Salary", "Freelance", "Investment", "Bonus", "Rental Income"]
EXPENSE_CATEGORIES = ["Rent", "Groceries", "Utilities", "Transport", "Entertainment", "Healthcare", "Education"]


def seed():
    init_db()
    db = SessionLocal()

    try:
        # ── Users ─────────────────────────────────────────────────────────────
        users_data = [
            {"email": "admin@finance.com",   "full_name": "Admin User",   "password": "Admin@123",   "role": Role.ADMIN},
            {"email": "analyst@finance.com", "full_name": "Ana Analyst",  "password": "Analyst@123", "role": Role.ANALYST},
            {"email": "viewer@finance.com",  "full_name": "Victor Viewer","password": "Viewer@123",  "role": Role.VIEWER},
        ]

        created_users = {}
        for data in users_data:
            existing = db.query(User).filter(User.email == data["email"]).first()
            if existing:
                print(f"⚠️  User {data['email']} already exists, skipping.")
                created_users[data["role"]] = existing
                continue

            user = User(
                email=data["email"],
                full_name=data["full_name"],
                hashed_password=get_password_hash(data["password"]),
                role=data["role"],
            )
            db.add(user)
            db.flush()
            created_users[data["role"]] = user
            print(f"✅  Created user: {data['email']} ({data['role']})")

        db.commit()

        # ── Transactions ──────────────────────────────────────────────────────
        admin_user = created_users.get(Role.ADMIN)
        if not admin_user:
            print("❌  Admin user not found, skipping transactions.")
            return

        today = date.today()
        transactions_to_create = []

        for i in range(60):  # 60 transactions over the last 6 months
            t_date = today - timedelta(days=random.randint(0, 180))
            t_type = random.choice([TransactionType.INCOME, TransactionType.EXPENSE])
            category = random.choice(
                INCOME_CATEGORIES if t_type == TransactionType.INCOME else EXPENSE_CATEGORIES
            )
            amount = Decimal(str(round(random.uniform(100, 5000), 2)))

            transactions_to_create.append(Transaction(
                amount=amount,
                type=t_type,
                category=category,
                date=t_date,
                notes=f"Sample {t_type.value} for {category}",
                created_by_id=admin_user.id,
            ))

        db.bulk_save_objects(transactions_to_create)
        db.commit()
        print(f"✅  Created {len(transactions_to_create)} sample transactions.")

        print("\n" + "═" * 50)
        print("🎉  Seed complete!")
        print("═" * 50)
        print("\n📋  Demo Credentials:")
        for data in users_data:
            print(f"   {data['role'].upper():10} → {data['email']} / {data['password']}")
        print("\n🌐  API Docs: http://localhost:8000/docs")

    except Exception as e:
        db.rollback()
        print(f"❌  Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
