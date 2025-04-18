from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
socketio = socketio = SocketIO(cors_allowed_origins="*", async_mode='eventlet')
