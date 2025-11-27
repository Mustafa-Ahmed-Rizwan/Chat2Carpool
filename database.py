from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    JSON,
    Float,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

# Neon DB connection
DATABASE_URL = os.getenv("DATABASE_URL")  # Your Neon DB connection string

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class RideRequest(Base):
    """Table for ride requests (passengers looking for rides)"""

    __tablename__ = "ride_requests"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)  # Phone number from WhatsApp

    # Ride details
    pickup_location = Column(String, nullable=False)
    drop_location = Column(String, nullable=False)
    route = Column(JSON, nullable=True)  # List of stops
    date = Column(String, nullable=False)
    time = Column(String, nullable=False)
    passengers = Column(Integer, nullable=False, default=1)
    additional_info = Column(String, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(
        Boolean, default=True
    )  # Can be deactivated after ride is completed
    is_matched = Column(Boolean, default=False)
    matched_with = Column(Integer, nullable=True)  # ID of matched ride offer

    def __repr__(self):
        return f"<RideRequest(id={self.id}, from={self.pickup_location}, to={self.drop_location})>"


class RideOffer(Base):
    """Table for ride offers (drivers offering rides)"""

    __tablename__ = "ride_offers"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)  # Phone number from WhatsApp

    # Ride details
    pickup_location = Column(String, nullable=False)
    drop_location = Column(String, nullable=False)
    route = Column(JSON, nullable=True)  # List of stops
    date = Column(String, nullable=False)
    time = Column(String, nullable=False)
    available_seats = Column(Integer, nullable=False)
    additional_info = Column(String, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    seats_filled = Column(Integer, default=0)  # Track how many seats are taken

    def __repr__(self):
        return f"<RideOffer(id={self.id}, from={self.pickup_location}, to={self.drop_location}, seats={self.available_seats})>"


class Match(Base):
    """Table to store matches between requests and offers"""

    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, nullable=False, index=True)
    offer_id = Column(Integer, nullable=False, index=True)

    # Match quality metrics
    match_type = Column(
        String, nullable=False
    )  # "exact", "partial_route", "time_flexible"
    match_score = Column(Float, nullable=False)  # 0.0 to 1.0

    # Status
    status = Column(String, default="pending")  # pending, accepted, rejected, completed
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Match(id={self.id}, request={self.request_id}, offer={self.offer_id}, score={self.match_score})>"


# Create all tables
def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
