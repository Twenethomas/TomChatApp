from flask import Blueprint, request, jsonify, url_for, session, redirect
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import func, case, and_, or_
from sqlalchemy.orm import aliased
from flask_socketio import emit
from werkzeug.security import generate_password_hash, check_password_hash
from models import Contacts, FriendRequest, Messages, Users
from extensions import db, socketio

user_bp = Blueprint('user', __name__)

@user_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    user = Users.query.filter_by(username=username).first()

    if user and check_password_hash(user.password, password):
        login_user(user)
        session['user_id'] = user.custom_id  # ✅ Store custom_id in session

        # Check if there's a `next` parameter (e.g., if the user was redirected from `/chat`)
        next_page = request.args.get('next')
        if next_page:
            return jsonify({"redirect": next_page})

        # Redirect admin to `/admin/dashboard`, others to `/chat`
        if user.is_admin:
            return jsonify({"redirect": url_for('admin.admin_dashboard')})
        return jsonify({"redirect": url_for('message.chat_page')})
    emit('update_status', {'user_id': user.custom_id, 'status': 'online'})
        
    return jsonify({"error": "Invalid credentials"}), 401


@user_bp.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    is_admin = data.get('is_admin', False)

    if isinstance(is_admin, str):
        is_admin = is_admin.lower() in ['true', '1', 'on', 'yes']

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    existing_user = Users.query.filter_by(username=username).first()
    if existing_user:
        return jsonify({"redirect": "login_tab", "message": "User already exists. Please log in."}), 200

    
    new_user = Users(
        username=username,
        password=generate_password_hash(password),
        is_admin=is_admin
    )

    db.session.add(new_user)
    db.session.commit()

    return jsonify({"success": True, "message": "Registration successful! Please log in."}), 201


@user_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    user= Users.query.filter_by(is_online=True)
    session.pop('user_id', None)  # ✅ Clear session
    emit('update_status', {'user_id': user.custom_id, 'status': 'offline'}, join_room=user.cudtom_id)
    
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
    friend_requests = [
        {
        "request_id": req.custom_id,
        "sender_id": req.sender_id
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
    socketio.emit('friend_request_declined', {
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
        return jsonify([]), 200

    current_user_id = current_user.custom_id

    # Get existing friend IDs
    existing_friends = FriendRequest.query.filter(
        (FriendRequest.status == 'accepted') &
        ((FriendRequest.sender_id == current_user_id) |
         (FriendRequest.receiver_id == current_user_id))
    ).all()

    friend_ids = {req.receiver_id if req.sender_id == current_user_id else req.sender_id
                  for req in existing_friends}

    # Alias the Users model for clarity in subqueries
    UserAlias = aliased(Users)

    # Modified subquery to determine friend request status: limit the subquery to 1 record,
    # ensuring that we get only the most recent (highest custom_id) status.
    request_status_subquery = (
        db.session.query(
            case(
                (FriendRequest.status == 'pending', 'pending'),
                (FriendRequest.status == 'accepted', 'accepted'),
                (FriendRequest.status == 'declined', 'declined'),
                else_='none'
            )
        )
        .filter(
            or_(
                and_(
                    FriendRequest.sender_id == current_user_id,
                    FriendRequest.receiver_id == UserAlias.custom_id
                ),
                and_(
                    FriendRequest.receiver_id == current_user_id,
                    FriendRequest.sender_id == UserAlias.custom_id
                )
            )
        )
        .order_by(FriendRequest.custom_id.desc())  # Order to pick the most recent record
        .limit(1)  # Limit the subquery to a single result
        .correlate(UserAlias)
        .scalar_subquery()
    )

    # Subquery to count mutual friends between current user and each potential friend
    mutual_friends_subquery = (
        db.session.query(func.count(FriendRequest.custom_id))
        .filter(
            or_(
                and_(
                    FriendRequest.sender_id == UserAlias.custom_id,
                    FriendRequest.receiver_id.in_(
                        db.session.query(FriendRequest.receiver_id)
                        .filter(
                            FriendRequest.sender_id == current_user_id,
                            FriendRequest.status == 'accepted'
                        )
                    )
                ),
                and_(
                    FriendRequest.receiver_id == UserAlias.custom_id,
                    FriendRequest.sender_id.in_(
                        db.session.query(FriendRequest.sender_id)
                        .filter(
                            FriendRequest.receiver_id == current_user_id,
                            FriendRequest.status == 'accepted'
                        )
                    )
                )
            ),
            FriendRequest.status == 'accepted'
        )
        .correlate(UserAlias)
        .scalar_subquery()
    )

    # Main query to search users
    query_filters = [
        UserAlias.username.ilike(f'%{query}%'),
        UserAlias.custom_id != current_user_id
    ]
    if friend_ids:
        query_filters.append(~UserAlias.custom_id.in_(friend_ids))

    users_query = (
        db.session.query(UserAlias)
        .filter(*query_filters)
        .add_columns(
            request_status_subquery.label('request_status'),
            mutual_friends_subquery.label('mutual_friends')
        )
        .order_by(
            case(
                (request_status_subquery == 'pending', 1),
                (request_status_subquery == 'accepted', 2),
                (request_status_subquery == 'none', 3)
            ),
            mutual_friends_subquery.desc(),
            UserAlias.username.asc()
        )
    )

    results = users_query.all()

    # Process the result rows
    users_data = []
    for user, request_status, mutual_friends in results:
        users_data.append({
            'custom_id': user.custom_id,
            'username': user.username,
            'profile_picture': user.profile_picture or 'default_profile.jpg',
            'mutual_friends': mutual_friends,
            'request_status': request_status
        })

    return jsonify(users_data), 200

@user_bp.route('/api/friends', methods=['GET'])
@login_required
def get_friends():
    friends = FriendRequest.query.filter(
        ((FriendRequest.sender_id == current_user.custom_id) | 
        (FriendRequest.receiver_id == current_user.custom_id)),
        FriendRequest.status == "accepted"
    ).all()
    
    friend_data = []
    for req in friends:
        friend_id = req.receiver_id if req.sender_id == current_user.custom_id else req.sender_id
        friend = Users.query.get(friend_id)
        if not friend:
            continue

        # Get unread message count
        unread_count = Messages.query.filter(
            Messages.sender_id == friend.custom_id,
            Messages.receiver_id == current_user.custom_id,
            Messages.is_read == False
        ).count()

        # Get last message between users
        last_message = Messages.query.filter(
            ((Messages.sender_id == current_user.custom_id) & 
            (Messages.receiver_id == friend.custom_id)) |
            ((Messages.sender_id == friend.custom_id) & 
            (Messages.receiver_id == current_user.custom_id))
        ).order_by(Messages.timestamp.desc()).first()

        friend_data.append({
            "custom_id": friend.custom_id,
            "username": friend.username,
            "profile_picture": friend.profile_picture,
            "last_seen": friend.last_seen.strftime('%H:%M') if friend.last_seen else '',
            "is_online": friend.is_online,
            "unread_count": unread_count,
            "last_message":{
            'text': last_message.message_text if last_message else None,
            'time': last_message.timestamp.strftime('%H:%M') if last_message else None
                }
            })


    # Sort friends by unread count (descending) and online status
    friend_data.sort(key=lambda x: (-x['unread_count'], -x['is_online']))
    
    return jsonify(friend_data), 200
