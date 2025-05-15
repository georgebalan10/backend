from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    is_admin = db.Column(db.Boolean, default=False)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    message = db.Column(db.Text)
    date = db.Column(db.String(20))
    time = db.Column(db.String(5))  # Ex: 13:00
    duration = db.Column(db.Integer)  # Durata în minute (ex: 30, 60)
    confirmed = db.Column(db.Boolean, default=False)
    duration_minutes = db.Column(db.Integer, nullable=True)
    user = db.relationship('User', backref='appointments')

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    text = db.Column(db.Text, nullable=False)
    date = db.Column(db.String(20), nullable=False)
    rating = db.Column(db.Integer, nullable=True) 
    user = db.relationship('User', backref=db.backref('reviews', lazy=True))

class Upload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    filename = db.Column(db.String(255))
    description = db.Column(db.String(255))
    user = db.relationship('User', backref=db.backref('uploads', lazy=True))
