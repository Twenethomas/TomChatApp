from flask import Blueprint, request, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import Contacts, Users, FriendRequest
from extensions import db, socketio
import uuid
from flask_socketio import emit

user_bp = Blueprint('user', __name__)

@user_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    user = Users.query.filter_by(username=username).first()
    if user and check_password_hash(user.password, password):
        login_user(user)
        session['user_id'] = user.custom_id
        return jsonify({'success': True, 'message': 'Login successful'}), 200
    else:
        return jsonify({'error': 'Invalid username or password'}), 401

@user_bp.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    is_admin = data.get('is_admin', False)
    if Users.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 400
    custom_id = f"FCM.41.008.{Users.query.count() + 1:03d}.{uuid.uuid4().hex[:4]}"
    if is_admin:
        new_user = Users(
            custom_id=custom_id,
            username=username,
            password=generate_password_hash(password),
            is_admin=True
        )
    else :
        new_user=Users(
            custom_id=custom_id,
            username=username,
            password=password,
            is_admin=False)
    db.session.add(new_user)
    db.session.commit()
    login()
    session['user_id'] = new_user.custom_id
    return jsonify({'success': True, 'message': 'Registration successful'}), 201

@user_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    session.pop('user_id', None)
    return jsonify({'success': True, 'message': 'Logout successful'}), 200

@user_bp.route('/api/friend_request', methods=['POST'])
@login_required
def send_friend_request():
    data = request.json
    receiver_id = data.get('receiver_id')
    existing_request = FriendRequest.query.filter_by(sender_id=current_user.custom_id, receiver_id=receiver_id).first()
    if existing_request:
        return jsonify({'error': 'Friend request already sent'}), 400
    new_request = FriendRequest(sender_id=current_user.custom_id, receiver_id=receiver_id)
    db.session.add(new_request)
    db.session.commit()
    socketio.emit('friend_request_received', {
        'request_id': new_request.custom_id,
        'sender_id': current_user.custom_id,
        'sender_username': current_user.username
    }, room=receiver_id)
    return jsonify({'success': True, 'message': 'Friend request sent'}), 201

@user_bp.route('/api/friend_requests', methods=['GET'])
@login_required
def get_friend_requests():
    requests = FriendRequest.query.filter_by(receiver_id=current_user.custom_id, status="pending").all()
    friend_requests = [{
        "request_id": req.custom_id,
        "sender_id": req.sender_id,
        "sender_username": req.sender.username
    } for req in requests]
    return jsonify(friend_requests), 200

@user_bp.route('/api/friend_request/decline/<request_id>', methods=['POST'])
@login_required
def decline_friend_request(request_id):
    friend_request = FriendRequest.query.filter_by(request_id=request_id).first()
    if not friend_request or friend_request.receiver_id != current_user.custom_id:
        return jsonify({'error': 'Invalid request'}), 400
    friend_request.status = "declined"
    db.session.commit()
    emit('friend_request_declined', {
        'request_id': request_id,
        'receiver_id': current_user.custom_id
    }, room=friend_request.sender_id)
    return jsonify({'success': True, 'message': 'Friend request declined'}), 200

@user_bp.route('/api/friend_request/accept/<request_id>', methods=['POST'])
@login_required
def accept_friend_request(request_id):
    friend_request =FriendRequest.query.filter_by(custom_id=request_id).first()
    if not friend_request or friend_request.receiver_id != current_user.custom_id:
        return jsonify({'error': 'Invalid request'}), 400
    friend_request.status = "accepted"
    db.session.commit()
    socketio.emit('friend_request_accepted', {
        'receiver_id': friend_request.receiver_id,
        'sender_id': friend_request.sender_id
    }, room=friend_request.sender_id)
    return jsonify({'success': True}), 200

@user_bp.route('/api/contacts', methods=['GET'])
@login_required
def get_contacts():
    contacts = Contacts.query.filter_by(user_id=current_user.custom_id).all()
    contacts_data = [{
        'username': contact.contact_user.username,
        'profile_picture': contact.contact_user.profile_picture,
        'status': contact.contact_user.status
    } for contact in contacts]
    return jsonify(contacts_data)

@user_bp.route('/api/search_users', methods=['GET'])
@login_required
def search_users():
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify([])
    users = Users.query.filter(Users.username.ilike(f'%{query}%')).filter(Users.custom_id != current_user.custom_id).all()
    users_data = [{
        'custom_id': user.custom_id,
        'username': user.username,
        'profile_picture': user.profile_picture or 'default_profile.jpg'
    } for user in users]
    return jsonify(users_data), 200

@user_bp.route('/api/friends', methods=['GET'])
@login_required
def get_friends():
    # Here, we consider accepted friend requests as friendships
    friends = FriendRequest.query.filter(
        ((FriendRequest.sender_id == current_user.custom_id) | (FriendRequest.receiver_id == current_user.custom_id)),
        FriendRequest.status == "accepted"
    ).all()
    friend_data = []
    for req in friends:
        friend_id = req.receiver_id if req.sender_id == current_user.custom_id else req.sender_id
        friend = Users.query.get(friend_id)
        if friend:
            friend_data.append({
                "custom_id": friend.custom_id,
                "username": friend.username,
                "profile_picture": friend.profile_picture,
                "last_seen": friend.last_seen,
                "is_online": friend.is_online
            })
    return jsonify(friend_data), 200
