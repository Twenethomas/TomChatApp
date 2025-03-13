import uuid
from datetime import datetime
from flask_login import UserMixin
from extensions import db
from sqlalchemy import event, text  # ✅ Import text

class Users(db.Model, UserMixin):
    custom_id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    profile_picture = db.Column(db.String(255), default='default_profile.jpg')
    is_admin = db.Column(db.Boolean, default=False)
    is_online = db.Column(db.Boolean, default=False)
    is_blocked = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(100), default="Available")
    last_seen = db.Column(db.DateTime)
    def get_id(self):  # ✅ Override this function properly
        return str(self.custom_id) 
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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

# ✅ Fix: Use text() to execute raw SQL
def create_database_triggers():
    with db.engine.connect() as connection:
        connection.execute(text("""
        -- ✅ TRIGGER: Prevent Admin Deletion
        CREATE OR ALTER TRIGGER prevent_admin_delete
        ON Users
        INSTEAD OF DELETE
        AS
        BEGIN
            IF EXISTS (SELECT 1 FROM deleted WHERE is_admin = 1)
            BEGIN
                RAISERROR ('Admins cannot be deleted.', 16, 1);
                RETURN;
            END
            DELETE FROM Users WHERE custom_id IN (SELECT custom_id FROM deleted);
        END;
        """))

        connection.execute(text("""
        -- ✅ STORED PROCEDURE: Block a User
        CREATE OR ALTER PROCEDURE BlockUser @userID VARCHAR(50)
        AS
        BEGIN
            UPDATE Users SET is_blocked = 1 WHERE custom_id = @userID;
        END;
        """))

        connection.execute(text("""
        -- ✅ FUNCTION: Get Online Users Count
        CREATE OR ALTER FUNCTION GetOnlineUsers()
        RETURNS INT
        AS
        BEGIN
            DECLARE @count INT;
            SELECT @count = COUNT(*) FROM Users WHERE is_online = 1;
            RETURN @count;
        END;
        """))

        connection.execute(text("""
        -- ✅ TRIGGER: Prevent Blocked Users' Messages from Being Deleted
        CREATE OR ALTER TRIGGER prevent_blocked_message_delete
        ON Messages
        INSTEAD OF DELETE
        AS
        BEGIN
            IF EXISTS (SELECT 1 FROM deleted d JOIN Users u ON d.sender_id = u.custom_id WHERE u.is_blocked = 1)
            BEGIN
                RAISERROR ('Blocked users’ messages cannot be deleted.', 16, 1);
                RETURN;
            END
            DELETE FROM Messages WHERE custom_id IN (SELECT custom_id FROM deleted);
        END;
        """))

        connection.execute(text("""
        -- ✅ STORED PROCEDURE: Delete all messages by a user
        CREATE OR ALTER PROCEDURE DeleteUserMessages @userID VARCHAR(50)
        AS
        BEGIN
            DELETE FROM Messages WHERE sender_id = @userID OR receiver_id = @userID;
        END;
        """))

        connection.execute(text("""
        -- ✅ TRIGGER: Prevent deletion of groups with members
        CREATE OR ALTER TRIGGER prevent_group_delete
        ON Groups
        INSTEAD OF DELETE
        AS
        BEGIN
            IF EXISTS (SELECT 1 FROM deleted d JOIN GroupMembers gm ON d.custom_id = gm.group_id)
            BEGIN
                RAISERROR ('Groups with members cannot be deleted.', 16, 1);
                RETURN;
            END
            DELETE FROM Groups WHERE custom_id IN (SELECT custom_id FROM deleted);
        END;
        """))

        connection.execute(text("""
        -- ✅ STORED PROCEDURE: Get all groups for a user
        CREATE OR ALTER PROCEDURE GetUserGroups @userID VARCHAR(50)
        AS
        BEGIN
            SELECT * FROM Groups WHERE created_by = @userID;
        END;
        """))

# ✅ Execute triggers & stored procedures after migration
@event.listens_for(db.metadata, "after_create")
def after_create(target, connection, **kw):
    create_database_triggers()
