"""
Seed Database with Mock Data

Populates the database with test data for development.
Run this inside the Docker container.
"""

import asyncio
import random
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select

from passlib.context import CryptContext
from app.config import settings
from app.database.models import (
    Base, Municipality, Property, SatelliteImagery, 
    Detection, ChangeDetection, Alert, User
)

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

async def seed_database():
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=True
    )
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        print("Seeding database with mock data...")
        
        # 1. Seed Users
        result = await db.execute(select(User).where(User.email == "admin@aikosh.gov.in"))
        if not result.scalar_one_or_none():
            admin_user = User(
                email="admin@aikosh.gov.in",
                hashed_password=get_password_hash("admin123"),
                full_name="System Administrator",
                role="admin",
                department="IT",
                is_active=True
            )
            db.add(admin_user)
            
            officer_user = User(
                email="officer@aikosh.gov.in",
                hashed_password=get_password_hash("officer123"),
                full_name="Municipal Officer",
                role="officer",
                department="MA&UD",
                is_active=True
            )
            db.add(officer_user)
            await db.flush()
            print("Created default users: admin@aikosh.gov.in, officer@aikosh.gov.in")
        
        # 2. Seed Municipalities
        result = await db.execute(select(Municipality))
        if result.scalar_one_or_none():
            print("Database already has geographical data, skipping geographical seed.")
            await db.commit()
            return
        
        municipalities = []
        muni_names = ["Guntur Municipal Corporation", "Vijayawada Municipal Corporation", "Vizag Municipal Corporation"]
        for i, name in enumerate(muni_names, 1):
            muni = Municipality(
                name=name,
                code=f"MUNI{i:03d}",
                district=name.split()[0],
                state="Andhra Pradesh"
            )
            db.add(muni)
            await db.flush()
            municipalities.append(muni)
        
        print(f"Created {len(municipalities)} municipalities")
        
        properties = []
        for muni in municipalities:
            for j in range(100):
                prop = Property(
                    property_id=f"PROP-{muni.code}-{j:04d}",
                    municipality_id=muni.id,
                    survey_number=f"SN/{random.randint(1,999)}/{random.choice(['A','B',''])}",
                    owner_name=f"Owner {random.randint(1, 1000)}",
                    property_type=random.choice(["residential", "commercial", "industrial", "vacant"]),
                    land_use=random.choice(["residential", "commercial", "agricultural", "mixed"]),
                    area_sqm=random.uniform(100, 2000),
                    built_area_sqm=random.uniform(50, 1500),
                    is_verified=random.random() > 0.3
                )
                db.add(prop)
                await db.flush()
                properties.append(prop)
        
        print(f"Created {len(properties)} properties")
        
        satellite_imagery = []
        satellites = ["Sentinel-2A", "Sentinel-2B", "Landsat-8"]
        for i in range(10):
            img = SatelliteImagery(
                scene_id=f"S2_{datetime.utcnow().strftime('%Y%m%d')}_{i:04d}",
                satellite=random.choice(satellites),
                sensor="MSI",
                acquisition_date=datetime.utcnow() - timedelta(days=random.randint(1, 365)),
                cloud_cover=random.uniform(0, 30),
                resolution_meters=10.0,
                is_processed=True,
                processing_status="completed"
            )
            db.add(img)
            await db.flush()
            satellite_imagery.append(img)
        
        print(f"Created {len(satellite_imagery)} satellite imagery records")
        
        detections = []
        detection_types = ["building", "road", "water"]
        for img in satellite_imagery:
            for k in range(random.randint(5, 15)):
                det = Detection(
                    imagery_id=img.id,
                    detection_type=random.choice(detection_types),
                    confidence=random.uniform(0.6, 0.99),
                    area_sqm=random.uniform(50, 500),
                    model_name="YOLOv8-Mock",
                    model_version="1.0",
                    is_verified=random.random() > 0.5
                )
                db.add(det)
                await db.flush()
                detections.append(det)
        
        print(f"Created {len(detections)} detections")
        
        changes = []
        change_types = ["new_construction", "expansion", "demolition", "vegetation_change"]
        severities = ["critical", "high", "medium", "low"]
        
        for i in range(min(20, len(satellite_imagery) - 1)):
            change = ChangeDetection(
                imagery_before_id=satellite_imagery[i].id,
                imagery_after_id=satellite_imagery[i + 1].id,
                change_type=random.choice(change_types),
                confidence=random.uniform(0.5, 0.95),
                severity=random.choice(severities),
                area_sqm=random.uniform(100, 1000),
                is_verified=random.random() > 0.5,
                is_authorised=random.choice([True, False, None])
            )
            db.add(change)
            await db.flush()
            changes.append(change)
        
        print(f"Created {len(changes)} change detections")
        
        alerts = []
        for change in changes[:15]:
            alert = Alert(
                change_detection_id=change.id,
                title=f"{change.change_type.replace('_', ' ').title()} Detected",
                description=f"Detected {change.change_type} with {change.severity} severity",
                severity=change.severity,
                status=random.choice(["new", "acknowledged", "resolved", "dismissed"]),
                municipality_id=random.choice(municipalities).id
            )
            db.add(alert)
            await db.flush()
            alerts.append(alert)
        
        print(f"Created {len(alerts)} alerts")
        
        await db.commit()
        print("\n✅ Database seeding completed!")
        print(f"   - Municipalities: {len(municipalities)}")
        print(f"   - Properties: {len(properties)}")
        print(f"   - Satellite Imagery: {len(satellite_imagery)}")
        print(f"   - Detections: {len(detections)}")
        print(f"   - Change Detections: {len(changes)}")
        print(f"   - Alerts: {len(alerts)}")


if __name__ == "__main__":
    asyncio.run(seed_database())
