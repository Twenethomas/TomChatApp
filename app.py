import os
from flask import Flask, render_template
from flask_migrate import Migrate
from flask_login import current_user
from config import Config
from extensions import db, socketio, login_manager
from datetime import datetime,timezone

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)# Ensure we use eventlet (or gevent) as the async mode
socketio.init_app(app, cors_allowed_origins="*", async_mode="eventlet", transports=["websocket"])
migrate = Migrate(app, db)
login_manager.init_app(app)
login_manager.login_view = 'user.login'


# Register Blueprints
from models import Users  # Needed for user_loader
from routes.user_routes import user_bp
from routes.message_routes import message_bp
from routes.contact_routes import contact_bp
from routes.group_routes import group_bp
from routes.admin_routes import admin_bp

app.register_blueprint(user_bp)
app.register_blueprint(message_bp)
app.register_blueprint(contact_bp)
app.register_blueprint(group_bp)
app.register_blueprint(admin_bp)

@app.route('/')
def index():
    return render_template('index.html')

@app.before_request
def update_last_seen():
    if current_user.is_authenticated:
        last_seen_time = datetime.now(timezone.utc)
        if current_user.last_seen != last_seen_time:
            current_user.last_seen = last_seen_time
            db.session.commit()


@login_manager.user_loader
def load_user(user_id):
    # Load user using the UUID string
    from models import Users
    return Users.query.filter_by(custom_id=user_id).first() or None

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 1000))
    with app.app_context():
        db.create_all()
    socketio.run(app, host="0.0.0.0", port=port, debug=True)
