from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO

db = SQLAlchemy()
login_manager = LoginManager()
socketio = SocketIO()

@login_manager.user_loader
def load_user(user_id):
    from models import Users
    return Users.query.get(user_id)
