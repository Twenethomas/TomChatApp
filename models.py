import uuid
from datetime import datetime
from flask_login import UserMixin
from extensions import db

class Users(db.Model, UserMixin):
    custom_id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    profile_picture = db.Column(db.String(255), default='default_profile.jpg')
    is_admin = db.Column(db.Boolean, default=False)
    is_online = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(100), default="Available")
    last_seen = db.Column(db.DateTime)

    def get_id(self):
        return self.custom_id

class Messages(db.Model):
    custom_id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    sender_id = db.Column(db.String(50), db.ForeignKey('users.custom_id'), nullable=False)
    receiver_id = db.Column(db.String(50), db.ForeignKey('users.custom_id'), nullable=False)
    message_text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Groups(db.Model):
    custom_id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    group_name = db.Column(db.String(100), nullable=False)
    created_by = db.Column(db.String(50), db.ForeignKey('users.custom_id'))

class GroupMembers(db.Model):
    custom_id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    group_id = db.Column(db.String(50), db.ForeignKey('groups.custom_id'))
    user_id = db.Column(db.String(50), db.ForeignKey('users.custom_id'))

class Contacts(db.Model):
    custom_id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(50), db.ForeignKey('users.custom_id'))
    contact_user_id = db.Column(db.String(50), db.ForeignKey('users.custom_id'))

class FriendRequest(db.Model):
    custom_id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    sender_id = db.Column(db.String(50), db.ForeignKey('users.custom_id'), nullable=False)
    receiver_id = db.Column(db.String(50), db.ForeignKey('users.custom_id'), nullable=False)
    status = db.Column(db.String(20), default="pending")
    
    # Relationships to easily access sender and receiver details
    sender = db.relationship("Users", foreign_keys=[sender_id])
    receiver = db.relationship("Users", foreign_keys=[receiver_id])
