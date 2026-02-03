import pandas as pd
import numpy as np
from sqlalchemy.orm import Session as DBSession
from models import Session, Mosque, Meter, Reading, User
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta
import hashlib
import streamlit as st

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, input_hash):
    return hash_password(password) == input_hash

def login_user(username, password):
    session = get_db_session()
    user = session.query(User).filter_by(username=username).first()
    session.close()
    
    if user and verify_password(password, user.password_hash):
        return user
    return None

def get_db_session():
    return Session()

@st.cache_data
def get_mosques():
    session = get_db_session()
    mosques = session.query(Mosque).all()
    session.close()
    return mosques

@st.cache_data
def get_meters(mosque_id):
    session = get_db_session()
    meters = session.query(Meter).filter_by(mosque_id=mosque_id).all()
    session.close()
    return meters

@st.cache_data
def get_consumption_stats(mosque_id=None):
    session = get_db_session()
    query = session.query(Reading).join(Meter).join(Mosque)
    
    if mosque_id:
        query = query.filter(Mosque.id == mosque_id)
        
    df = pd.read_sql(query.statement, session.bind)
    session.close()
    
    if df.empty:
        return 0, 0, pd.DataFrame()

    total_consumption = (df['value'].max() - df['value'].min()) # Simple approximation for total
    # Better logic: Sum daily deltas if available, or just max-min of readings
    # Since we simulate readings, we can calculate daily consumption
    df = df.sort_values('date')
    # Calculate daily consumption (diff)
    # Group by meter to ensure diff is correct
    df['daily_consumption'] = df.groupby('meter_id')['value'].diff().fillna(0)
    
    total_cons = df['daily_consumption'].sum()
    total_cost = df['cost'].sum()
    
    return total_cons, total_cost, df

@st.cache_data
def get_chart_data(mosque_id=None, meter_type=None, start_date=None, end_date=None):
    session = get_db_session()
    # Explicitly select Reading and joined columns
    query = session.query(
        Reading.date.label('date'), 
        Reading.value.label('value'), 
        Reading.cost.label('cost'), 
        Reading.meter_id.label('meter_id'), 
        Meter.mosque_id.label('mosque_id'), 
        Meter.type.label('type')
    ).join(Meter).join(Mosque)
    
    if mosque_id:
        query = query.filter(Mosque.id == mosque_id)
    if meter_type:
        query = query.filter(Meter.type == meter_type)
    if start_date:
        query = query.filter(Reading.date >= start_date)
    if end_date:
        query = query.filter(Reading.date <= end_date)
        
    df = pd.read_sql(query.statement, session.bind)
    session.close()
    
    if df.empty:
        return pd.DataFrame()
        
    df['date'] = pd.to_datetime(df['date'])
    df['daily_consumption'] = df.groupby('meter_id')['value'].diff().fillna(0)
    # Fix: First reading of a period shouldn't be 0 if we filter, 
    # but for this POC diff is okay. In real app, we need prev reading outside range.
    
    return df

from sklearn.metrics import r2_score

@st.cache_data
def predict_usage(meter_id):
    session = get_db_session()
    # Fetch data
    readings = session.query(Reading).filter_by(meter_id=meter_id).order_by(Reading.date).all()
    session.close()
    
    if len(readings) < 30:
        return pd.DataFrame(), 0.0, 0.0
        
    df = pd.DataFrame([(r.date, r.value) for r in readings], columns=['ds', 'y'])
    df['ds'] = pd.to_datetime(df['ds'])
    
    # Calculate daily usage
    df['usage'] = df['y'].diff().fillna(0)
    df = df[1:] # Drop first NaN
    
    # Train
    df['date_ordinal'] = df['ds'].map(pd.Timestamp.toordinal)
    X = df[['date_ordinal']]
    y = df['usage']
    
    model = LinearRegression()
    model.fit(X, y)
    
    # Calculate Accuracy
    y_pred_train = model.predict(X)
    accuracy = r2_score(y, y_pred_train)
    
    # Predict
    last_date = df['ds'].max()
    future_dates = [last_date + timedelta(days=x) for x in range(1, 31)]
    future_ordinals = np.array([d.toordinal() for d in future_dates]).reshape(-1, 1)
    
    preds = model.predict(future_ordinals)
    
    future_df = pd.DataFrame({
        'ds': future_dates,
        'y': preds,
        'type': 'Predicted'
    })
    
    hist_df = df[['ds', 'usage']].rename(columns={'usage': 'y'})
    hist_df['type'] = 'Historical'
    
    result = pd.concat([hist_df, future_df])
    
    return result, preds.mean(), accuracy

def add_reading(meter_id, date_obj, value, cost=0):
    session = get_db_session()
    # Check if reading exists for this date? (Optional, skipping for simple POC)
    
    # Simple logic: If value provided is total reading, we just add it.
    # If it's consumption, we might need to handle differently. 
    # The models rely on 'value' being the cumulative meter reading.
    
    reading = Reading(
        meter_id=meter_id,
        date=date_obj,
        value=value,
        cost=cost
    )
    session.add(reading)
    session.commit()
    session.close()
    session.add(reading)
    session.commit()
    session.close()
    st.cache_data.clear()
    return True

def create_mosque(name, location, capacity):
    session = get_db_session()
    mosque = Mosque(name=name, location=location, capacity=capacity)
    session.add(mosque)
    session.commit()
    session.close()
    st.cache_data.clear()
    return True

def delete_mosque(mosque_id):
    session = get_db_session()
    # meters will be deleted by cascade if we configured it, but let's be manual for safety in POC
    # simplified for POC
    session.query(Mosque).filter(Mosque.id == mosque_id).delete()
    session.commit()
    session.close()
    st.cache_data.clear()
    return True

def create_meter(mosque_id, type):
    session = get_db_session()
    meter = Meter(mosque_id=mosque_id, type=type)
    session.add(meter)
    session.commit()
    session.close()
    st.cache_data.clear()
    return True

def delete_meter(meter_id):
    session = get_db_session()
    session.query(Meter).filter(Meter.id == meter_id).delete()
    session.commit()
    session.close()
    st.cache_data.clear()
    return True

def create_user(username, password, role):
    session = get_db_session()
    # check if exists
    if session.query(User).filter_by(username=username).first():
        session.close()
        return False
    
    user = User(username=username, password_hash=hash_password(password), role=role)
    session.add(user)
    session.commit()
    session.close()
    return True

def process_csv_upload(file):
    session = get_db_session()
    try:
        df = pd.read_csv(file)
        # Expected columns: meter_id, date, value, cost
        required = {'meter_id', 'date', 'value'}
        if not required.issubset(df.columns):
            return False, "Missing columns: meter_id, date, value"
        
        objects = []
        for _, row in df.iterrows():
            meter_id = int(row['meter_id'])
            date_obj = pd.to_datetime(row['date']).date()
            val = float(row['value'])
            cost = float(row.get('cost', 0))
            
            objects.append(Reading(meter_id=meter_id, date=date_obj, value=val, cost=cost))
            
        session.add_all(objects)
        session.commit()
        count = len(objects)
        session.close()
        st.cache_data.clear()
        return True, f"Successfully added {count} readings"
    except Exception as e:
        session.close()
        return False, str(e)

