from extension import db

class Users(db.Model):
    custom_id = db.Column(db.String(50), primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(100), default='Hey there! I am using TomChat.')
    last_seen = db.Column(db.DateTime, default=db.func.current_timestamp())

class Contacts(db.Model):
    custom_id = db.Column(db.String(50), primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('users.custom_id'))
    contact_user_id = db.Column(db.String(50), db.ForeignKey('users.custom_id'))

class Groups(db.Model):
    custom_id = db.Column(db.String(50), primary_key=True)
    group_name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class GroupMembers(db.Model):
    custom_id = db.Column(db.String(50), primary_key=True)
    group_id = db.Column(db.String(50), db.ForeignKey('groups.custom_id'))
    user_id = db.Column(db.String(50), db.ForeignKey('users.custom_id'))

class Messages(db.Model):
    custom_id = db.Column(db.String(50), primary_key=True)
    sender_id = db.Column(db.String(50), db.ForeignKey('users.custom_id'))
    receiver_id = db.Column(db.String(50), db.ForeignKey('users.custom_id'))
    message_text = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    is_read = db.Column(db.Boolean, default=False)