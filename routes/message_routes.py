from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from flask_socketio import SocketIO, emit, join_room
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import os
from datetime import datetime

app = Flask(__name__,static_folder=os.path.abspath("static"),template_folder=os.path.abspath("templates"))
app.config['SECRET_KEY'] = '1234'

# Update the following URI with your SQL Server credentials.
app.config['SQLALCHEMY_DATABASE_URI'] = 'mssql+pyodbc://@localhost/TomChat?driver=ODBC+Driver+18+for+SQL+Server&Trusted_Connection=yes&TrustServerCertificate=yes'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
socketio = SocketIO(app, cors_allowed_origins="*")  # Enable WebSocket

login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Custom ID generator (ensures ID fits within 50 characters)
def generate_custom_id():
    return f"FCM.41.008.230.23-{str(uuid.uuid4())[:6]}-{str(abs(hash(str(uuid.uuid4()))) % 100000)}"

# User Model

class Users(db.Model, UserMixin):
    __tablename__ = 'users'
    custom_id = db.Column(db.String(50), primary_key=True, default=generate_custom_id)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(100), default="Hey there! I am using TomChat.")
    last_seen = db.Column(db.DateTime, server_default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def get_id(self):
        return self.custom_id


# Message Model
class Messages(db.Model):
    __tablename__ = 'messages'
    custom_id = db.Column(db.String(50), primary_key=True, default=generate_custom_id)
    sender_id = db.Column(db.String(50), db.ForeignKey('users.custom_id'), nullable=False)
    receiver_id = db.Column(db.String(50), db.ForeignKey('users.custom_id'), nullable=False)
    message_text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    is_read = db.Column(db.Boolean, default=False)

# Flask-Login user loader
@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(user_id)

# Home Page
@app.route('/')
def index():
    return render_template('index.html')

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = Users.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('chat_page'))  # ✅ Redirect to chat page
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html')

# Registration Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if Users.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
        else:
            new_user = Users(
                username=username,
                password=generate_password_hash(password)
            )
            db.session.add(new_user)
            db.session.commit()

            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))

    return render_template('register.html')
@app.before_request
def update_last_seen():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()

# Chat Route (Retrieves Chat History)
# @app.route('/chat_home')
# @login_required
# def chat_home():
#     users = Users.query.filter(Users.custom_id != current_user.custom_id).all()

#     # Debugging: Print the list of users
#     print("Users fetched for sidebar:", users)

#     return render_template('chat.html', users=users)

# Fetch Messages API (For AJAX/Frontend Fetch)
@app.route('/messages/<receiver_id>')
@login_required
def get_messages(receiver_id):
    messages = Messages.query.filter(
        ((Messages.sender_id == current_user.custom_id) & (Messages.receiver_id == receiver_id)) |
        ((Messages.sender_id == receiver_id) & (Messages.receiver_id == current_user.custom_id))
    ).order_by(Messages.timestamp.asc()).all()

    messages_data = [
        {"sender_id": msg.sender_id, "message_text": msg.message_text, "timestamp": msg.timestamp}
        for msg in messages
    ]

    return jsonify(messages_data)
@app.route('/chat_page')
@login_required
def chat_page():
    users = Users.query.filter(Users.custom_id != current_user.custom_id).all()
    
    # Debugging: Print the list of users in the console
    print("Users fetched for sidebar:", users)

    return render_template('chat.html', users=users)

# Logout Route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

# SocketIO Events
@socketio.on('send_message')
def handle_send_message(data):
    message_text = data['message']
    sender_id = data['sender_id']
    receiver_id = data['receiver_id']

    # Save message to database
    new_message = Messages(
        sender_id=sender_id,
        receiver_id=receiver_id,
        message_text=message_text
    )
    db.session.add(new_message)
    db.session.commit()

    # Emit message to receiver
    emit('receive_message', {
        'sender_id': sender_id,
        'message': message_text
    }, room=receiver_id)

@socketio.on('join_chat')
def handle_join_chat(data):
    user_id = data['user_id']
    join_room(user_id)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True)
