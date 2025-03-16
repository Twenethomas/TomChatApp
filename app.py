import os
from flask import Flask, render_template
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
from config import Config
from extensions import db, socketio, login_manager
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
socketio.init_app(app, cors_allowed_origins="*")
migrate = Migrate(app, db)
login_manager.init_app(app)
login_manager.login_view = 'user.login'

# Register Blueprints
from models import Users
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
        current_user.last_seen = datetime.utcnow()
        db.session.commit()

@login_manager.user_loader
def load_user(user_id):
    return Users.query.filter_by(custom_id=user_id).first()  # ✅ Load user by custom_id


if __name__ == '__main__':
    with app.app_context():
        socketio.run(app, host="0.0.0.0", port=5000, debug=True)
