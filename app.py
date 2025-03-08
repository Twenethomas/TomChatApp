from flask import Flask
from flask_socketio import SocketIO
from config import Config
from extension import db

app = Flask(__name__)
app.config.from_object(Config)

# Initialize db with the app
db.init_app(app)

# Initialize Flask-SocketIO
socketio = SocketIO(app)

# Import routes and models
with app.app_context():
    from models import *
    from routes.message_routes import *

from flask import request
from datetime import datetime

@app.before_request
def update_last_seen():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()

if __name__ == '__main__':
    socketio.run(app, debug=True)