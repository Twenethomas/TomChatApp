from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO

db = SQLAlchemy()
login_manager = LoginManager()
socketio = SocketIO()

@login_manager.user_loader
def load_user(username):
    from models import Users
    return Users.query.filter_by(username=username).first()

