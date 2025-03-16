import uuid
from datetime import datetime
from flask_login import UserMixin
from extensions import db
from sqlalchemy import event, text

# ----------------------
# Database Models
# ----------------------

class Users(db.Model, UserMixin):
    __tablename__ = 'users'
    custom_id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    profile_picture = db.Column(db.String(255), default='static/images/default_profile.jpg')
    is_admin = db.Column(db.Boolean, default=False)
    is_online = db.Column(db.Boolean, default=False, index=True)
    is_blocked = db.Column(db.Boolean, default=False, index=True)
    status = db.Column(db.String(100), default="Available")
    last_seen = db.Column(db.DateTime)
    
    # sent_requests = db.relationship('FriendRequest', foreign_keys='FriendRequest.sender_id', back_populates='sender')
    # received_requests = db.relationship('FriendRequest', foreign_keys='FriendRequest.receiver_id', back_populates='receiver')
 
    def get_id(self):
        return str(self.custom_id)

class Messages(db.Model):
    __tablename__ = 'messages'
    custom_id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    sender_id = db.Column(db.String(50), db.ForeignKey('users.custom_id'), nullable=False)  # CASCADE removed
    receiver_id = db.Column(db.String(50), db.ForeignKey('users.custom_id'), nullable=False)  # CASCADE removed
    message_text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    is_read = db.Column(db.Boolean, default=False, index=True)

class Groups(db.Model):
    __tablename__ = 'groups'
    custom_id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    group_name = db.Column(db.String(100), nullable=False)
    created_by = db.Column(db.String(50), db.ForeignKey('users.custom_id', ondelete='SET NULL'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class GroupMembers(db.Model):
    __tablename__ = 'groupmembers'
    group_id = db.Column(db.String(50), db.ForeignKey('groups.custom_id', ondelete='CASCADE'), primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('users.custom_id', ondelete='CASCADE'), primary_key=True)
    __table_args__ = (db.UniqueConstraint('group_id', 'user_id', name='uq_group_member'),)

class Contacts(db.Model):
    __tablename__ = 'contacts'
    custom_id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(50), db.ForeignKey('users.custom_id'), nullable=False)  # CASCADE removed
    contact_user_id = db.Column(db.String(50), db.ForeignKey('users.custom_id'), nullable=False)  # CASCADE removed
    __table_args__ = (db.UniqueConstraint('user_id', 'contact_user_id', name='uq_contact'),)

class FriendRequest(db.Model):
    __tablename__ = 'friendrequest'
    custom_id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    sender_id = db.Column(db.String(50), db.ForeignKey('users.custom_id'), nullable=False)
    receiver_id = db.Column(db.String(50), db.ForeignKey('users.custom_id'), nullable=False)
    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # # Add relationships
    # sender = db.relationship('User', foreign_keys=[sender_id], back_populates='sent_requests')
    # receiver = db.relationship('User', foreign_keys=[receiver_id], back_populates='received_requests')


class Settings(db.Model):
    custom_id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    last_modified = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
# ----------------------
# SQL Server Triggers & Procedures
# ----------------------

def create_database_triggers():
    with db.engine.connect() as connection:
        # Delete orphaned contacts when a user is deleted
        connection.execute(text("""
        CREATE OR ALTER TRIGGER delete_user_contacts
        ON users
        AFTER DELETE
        AS
        BEGIN
            DELETE FROM contacts 
            WHERE user_id IN (SELECT custom_id FROM deleted)
               OR contact_user_id IN (SELECT custom_id FROM deleted);
        END;
        """))
        
        # Delete orphaned messages when a user is deleted
        connection.execute(text("""
        CREATE OR ALTER TRIGGER delete_user_messages
        ON users
        AFTER DELETE
        AS
        BEGIN
            DELETE FROM messages 
            WHERE sender_id IN (SELECT custom_id FROM deleted)
               OR receiver_id IN (SELECT custom_id FROM deleted);
        END;
        """))
        
        # Delete orphaned friend requests when a user is deleted
        connection.execute(text("""
        CREATE OR ALTER TRIGGER delete_user_friend_requests
        ON users
        AFTER DELETE
        AS
        BEGIN
            DELETE FROM friendrequest 
            WHERE sender_id IN (SELECT custom_id FROM deleted)
               OR receiver_id IN (SELECT custom_id FROM deleted);
        END;
        """))
        
        # Existing triggers (prevent admin/group/message deletion)
        connection.execute(text("""
        CREATE OR ALTER TRIGGER prevent_admin_delete
        ON users
        INSTEAD OF DELETE
        AS
        BEGIN
            IF EXISTS (SELECT 1 FROM deleted WHERE is_admin = 1)
            BEGIN
                RAISERROR('Admins cannot be deleted.', 16, 1);
                ROLLBACK TRANSACTION;
                RETURN;
            END
            DELETE FROM users WHERE custom_id IN (SELECT custom_id FROM deleted);
        END;
        """))
        
        connection.execute(text("""
        CREATE OR ALTER TRIGGER prevent_group_delete
        ON groups
        INSTEAD OF DELETE
        AS
        BEGIN
            IF EXISTS (SELECT 1 FROM deleted d JOIN groupmembers gm ON d.custom_id = gm.group_id)
            BEGIN
                RAISERROR('Groups with members cannot be deleted.', 16, 1);
                ROLLBACK TRANSACTION;
                RETURN;
            END
            DELETE FROM groups WHERE custom_id IN (SELECT custom_id FROM deleted);
        END;
        """))
        
        connection.execute(text("""
        CREATE OR ALTER TRIGGER prevent_blocked_message_delete
        ON messages
        INSTEAD OF DELETE
        AS
        BEGIN
            IF EXISTS (SELECT 1 FROM deleted d JOIN users u ON d.sender_id = u.custom_id WHERE u.is_blocked = 1)
            BEGIN
                RAISERROR('Blocked users’ messages cannot be deleted.', 16, 1);
                ROLLBACK TRANSACTION;
                RETURN;
            END
            DELETE FROM messages WHERE custom_id IN (SELECT custom_id FROM deleted);
        END;
        """))
        
        # Stored Procedures
        connection.execute(text("""
        CREATE OR ALTER PROCEDURE BlockUser @userID VARCHAR(50)
        AS
        BEGIN
            UPDATE users SET is_blocked = 1 WHERE custom_id = @userID;
        END;
        """))
        
        connection.execute(text("""
        CREATE OR ALTER PROCEDURE GetUserGroups @userID VARCHAR(50)
        AS
        BEGIN
            SELECT g.* FROM groups g
            JOIN groupmembers gm ON g.custom_id = gm.group_id
            WHERE gm.user_id = @userID;
        END;
        """))

# ----------------------
# Execute After Database Creation
# ----------------------
@event.listens_for(db.metadata, "after_create")
def after_create(target, connection, **kw):
    create_database_triggers()