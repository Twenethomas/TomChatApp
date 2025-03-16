import uuid
from datetime import datetime
from flask_login import UserMixin
from sqlalchemy import text
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

    # # Add relationships
    # sender = db.relationship('User', foreign_keys=[sender_id], back_populates='sent_requests')
    # receiver = db.relationship('User', foreign_keys=[receiver_id], back_populates='received_requests')


class Settings(db.Model):
    __tablename__ = 'settings'
    custom_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # ✅ Changed to UUID
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
        CREATE OR REPLACE FUNCTION delete_user_contacts()
        RETURNS TRIGGER AS $$
        BEGIN
            DELETE FROM contacts 
            WHERE user_id IN (SELECT custom_id FROM OLD)
               OR contact_user_id IN (SELECT custom_id FROM OLD);
            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER delete_user_contacts_trigger
        AFTER DELETE ON users
        FOR EACH ROW
        EXECUTE FUNCTION delete_user_contacts();
        """))
        
        # Delete orphaned messages when a user is deleted
        connection.execute(text("""
        CREATE OR REPLACE FUNCTION delete_user_messages()
        RETURNS TRIGGER AS $$
        BEGIN
            DELETE FROM messages 
            WHERE sender_id IN (SELECT custom_id FROM OLD)
               OR receiver_id IN (SELECT custom_id FROM OLD);
            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER delete_user_messages_trigger
        AFTER DELETE ON users
        FOR EACH ROW
        EXECUTE FUNCTION delete_user_messages();
        """))
        
        # Delete orphaned friend requests when a user is deleted
        connection.execute(text("""
        CREATE OR REPLACE FUNCTION delete_user_friend_requests()
        RETURNS TRIGGER AS $$
        BEGIN
            DELETE FROM friendrequest 
            WHERE sender_id IN (SELECT custom_id FROM OLD)
               OR receiver_id IN (SELECT custom_id FROM OLD);
            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER delete_user_friend_requests_trigger
        AFTER DELETE ON users
        FOR EACH ROW
        EXECUTE FUNCTION delete_user_friend_requests();
        """))
        
        # Prevent admin deletion
        connection.execute(text("""
        CREATE OR REPLACE FUNCTION prevent_admin_delete()
        RETURNS TRIGGER AS $$
        BEGIN
            IF EXISTS (SELECT 1 FROM OLD WHERE is_admin = TRUE) THEN
                RAISE EXCEPTION 'Admins cannot be deleted.';
            END IF;
            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER prevent_admin_delete_trigger
        BEFORE DELETE ON users
        FOR EACH ROW
        EXECUTE FUNCTION prevent_admin_delete();
        """))
        
        # Prevent group deletion if it has members
        connection.execute(text("""
        CREATE OR REPLACE FUNCTION prevent_group_delete()
        RETURNS TRIGGER AS $$
        BEGIN
            IF EXISTS (SELECT 1 FROM groupmembers WHERE group_id = OLD.custom_id) THEN
                RAISE EXCEPTION 'Groups with members cannot be deleted.';
            END IF;
            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER prevent_group_delete_trigger
        BEFORE DELETE ON groups
        FOR EACH ROW
        EXECUTE FUNCTION prevent_group_delete();
        """))
        
        # Prevent blocked message deletion
        connection.execute(text("""
        CREATE OR REPLACE FUNCTION prevent_blocked_message_delete()
        RETURNS TRIGGER AS $$
        BEGIN
            IF EXISTS (SELECT 1 FROM users WHERE custom_id = OLD.sender_id AND is_blocked = TRUE) THEN
                RAISE EXCEPTION 'Blocked users’ messages cannot be deleted.';
            END IF;
            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER prevent_blocked_message_delete_trigger
        BEFORE DELETE ON messages
        FOR EACH ROW
        EXECUTE FUNCTION prevent_blocked_message_delete();
        """))

def create_database_procedures():
    with db.engine.connect() as connection:
        # Block a user
        connection.execute(text("""
        CREATE OR REPLACE FUNCTION block_user(user_id UUID)
        RETURNS VOID AS $$
        BEGIN
            UPDATE users SET is_blocked = TRUE WHERE custom_id = user_id;
        END;
        $$ LANGUAGE plpgsql;
        """))
        
        # Get user groups
        connection.execute(text("""
        CREATE OR REPLACE FUNCTION get_user_groups(user_id UUID)
        RETURNS TABLE (
            custom_id UUID,
            group_name VARCHAR(100),
            created_by UUID,
            created_at TIMESTAMP
        ) AS $$
        BEGIN
            RETURN QUERY
            SELECT g.* FROM groups g
            JOIN groupmembers gm ON g.custom_id = gm.group_id
            WHERE gm.user_id = user_id;
        END;
        $$ LANGUAGE plpgsql;
        """))
