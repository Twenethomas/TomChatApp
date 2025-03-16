import uuid
from datetime import datetime
from flask_login import UserMixin
from extensions import db
from sqlalchemy.dialects.postgresql import UUID

# ----------------------
# Database Models
# ----------------------

class Users(db.Model, UserMixin):
    __tablename__ = 'users'
    custom_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    profile_picture = db.Column(db.String(255), default='static/images/default_profile.jpg')
    is_admin = db.Column(db.Boolean, default=False)
    is_online = db.Column(db.Boolean, default=False, index=True)
    is_blocked = db.Column(db.Boolean, default=False, index=True)
    status = db.Column(db.String(100), default="Available")
    last_seen = db.Column(db.DateTime)

    def get_id(self):
        return str(self.custom_id)

class Messages(db.Model):
    __tablename__ = 'messages'
    custom_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sender_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.custom_id'), nullable=False)
    receiver_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.custom_id'), nullable=False)
    message_text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    is_read = db.Column(db.Boolean, default=False, index=True)

class Groups(db.Model):
    __tablename__ = 'groups'
    custom_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_name = db.Column(db.String(100), nullable=False)
    created_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.custom_id', ondelete='SET NULL'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class GroupMembers(db.Model):
    __tablename__ = 'groupmembers'
    group_id = db.Column(UUID(as_uuid=True), db.ForeignKey('groups.custom_id', ondelete='CASCADE'), primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.custom_id', ondelete='CASCADE'), primary_key=True)

class Contacts(db.Model):
    __tablename__ = 'contacts'
    custom_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.custom_id'), nullable=False)
    contact_user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.custom_id'), nullable=False)

class FriendRequest(db.Model):
    __tablename__ = 'friendrequest'
    custom_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sender_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.custom_id'), nullable=False)
    receiver_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.custom_id'), nullable=False)
    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
