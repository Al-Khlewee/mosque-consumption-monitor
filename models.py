import random
import math
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey, Enum
import enum
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

import os

Base = declarative_base()
DB_NAME = "mosques_v3.db"
# Use absolute path to ensure DB is created in the expected location
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, DB_NAME)

engine = create_engine(
    f"sqlite:///{DB_FILE}",
    connect_args={'check_same_thread': False} # Important for Streamlit
)
Session = sessionmaker(bind=engine)

class Mosque(Base):
    __tablename__ = 'mosques'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    location = Column(String)
    capacity = Column(Integer)
    meters = relationship("Meter", back_populates="mosque")

class Meter(Base):
    __tablename__ = 'meters'
    id = Column(Integer, primary_key=True)
    type = Column(String, nullable=False) # Electricity / Water
    mosque_id = Column(Integer, ForeignKey('mosques.id'))
    mosque = relationship("Mosque", back_populates="meters")
    readings = relationship("Reading", back_populates="meter")

class UserRole(enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False) # stored as string for simplicity in sqlite

class Reading(Base):
    __tablename__ = 'readings'
    id = Column(Integer, primary_key=True)
    meter_id = Column(Integer, ForeignKey('meters.id'))
    value = Column(Float)
    date = Column(Date)
    cost = Column(Float)
    meter = relationship("Meter", back_populates="readings")

def seed_data():
    Base.metadata.create_all(engine)
    session = Session()
    
    # Check if data exists
    if session.query(Mosque).count() > 0:
        session.close()
        print("Data already exists. Please delete 'mosques.db' to regenerate.")
        return

        print("Data already exists. Please delete 'mosques.db' to regenerate.")
        return

    print("Seeding realistic data...")
    
    # create default users
    # using simple sha256 for POC transparency in seeding, but real app uses utils.hash_password
    import hashlib
    def simple_hash(pwd):
        return hashlib.sha256(pwd.encode()).hexdigest()

    admin = User(username="admin", password_hash=simple_hash("admin123"), role="admin")
    manager = User(username="manager", password_hash=simple_hash("manager123"), role="manager")
    session.add(admin)
    session.add(manager)
    session.flush()
    
    mosques_data = [
        ("Masjid Al-Nour", "Downtown", 1000),
        ("Masjid Al-Falah", "North", 500),
        ("Masjid Al-Rahman", "East", 1200),
        ("Masjid Al-Tawa", "West", 300),
        ("Masjid Al-Ikhlas", "Suburbs", 800)
    ]

    for m_name, m_loc, m_cap in mosques_data:
        mosque = Mosque(name=m_name, location=m_loc, capacity=m_cap)
        session.add(mosque)
        session.flush()

        # Add Meters
        for m_type in ['Electricity', 'Water']:
            meter = Meter(type=m_type, mosque_id=mosque.id)
            session.add(meter)
            session.flush()

            # Generate Readings (2 years for better trend visibility)
            days_history = 730
            start_date = datetime.now().date() - timedelta(days=days_history)
            curr_val = 10000.0
            
            readings = []
            
            # Base load factors
            base_load = m_cap * (0.5 if m_type == 'Electricity' else 0.05)
            
            for day in range(days_history):
                date_obj = start_date + timedelta(days=day)
                day_of_year = date_obj.timetuple().tm_yday
                weekday = date_obj.weekday() # 0=Mon, 4=Fri
                
                # 1. Seasonality (Sine wave peaking in Summer ~Day 200)
                # Normalize day of year to 0-2pi
                season_factor = math.sin((day_of_year - 110) / 365.0 * 2 * math.pi) 
                # Shift to 0-1 range roughly, summer (positive) gets boost
                season_multiplier = 1 + (0.5 * season_factor) # +50% in peak summer, -50% in peak winter
                
                # 2. Weekly Pattern (Fridays are busier)
                friday_multiplier = 1.3 if weekday == 4 else 1.0
                
                # 3. Random noise
                noise = random.uniform(0.9, 1.1)
                
                daily_usage = base_load * season_multiplier * friday_multiplier * noise
                
                # Ensure positive
                daily_usage = max(daily_usage, 1.0)
                
                curr_val += daily_usage
                
                # Pricing
                rate = 0.18 if m_type == 'Electricity' else 6.0
                if m_type == 'Electricity' and daily_usage > 6000: # Tiered pricing simulation
                    rate = 0.30
                
                cost = daily_usage * rate
                
                readings.append(Reading(
                    meter_id=meter.id,
                    value=round(curr_val, 2),
                    date=date_obj,
                    cost=round(cost, 2)
                ))
            
            session.add_all(readings)
    
    session.commit()
    session.close()
    print("Seeding complete.")

if __name__ == "__main__":
    seed_data()
