from datetime import datetime
from database import db

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False) # Store hashed passwords

class Call(db.Model):
    __tablename__ = 'calls'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    preferred_time = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), default='Pending') # States: 'Pending', 'In Progress', 'Resolved'
    resolution = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)