from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from flask_socketio import emit, join_room, leave_room
from models import Messages, Users
from extensions import db, socketio
from datetime import datetime
import uuid

message_bp = Blueprint('message', __name__)

@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        user = Users.query.get(current_user.custom_id)
        if user:
            user.is_online = True
            db.session.commit()
            join_room(user.custom_id)
            emit('update_status', {'user_id': user.custom_id, 'status': 'online'}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated:
        user = Users.query.get(current_user.custom_id)
        if user:
            user.is_online = False
            db.session.commit()
            leave_room(user.custom_id)
            emit('update_status', {'user_id': user.custom_id, 'status': 'offline'}, broadcast=True)

@message_bp.route('/api/send_message', methods=['POST'])
@login_required
def send_message():
    data = request.json
    receiver_id = data.get('receiver_id')
    message_text = data.get('message')
    if not receiver_id or not message_text:
        return jsonify({'error': 'Missing receiver or message text'}), 400

    new_message = Messages(
        sender_id=current_user.custom_id,
        receiver_id=receiver_id,
        message_text=message_text,
        timestamp=datetime.utcnow()
    )
    db.session.add(new_message)
    db.session.commit()
    sender= Users.query.filter_by(custom_id = current_user.custom_id).first()
    socketio.emit('receive_message', {
        'sender_id': current_user.custom_id,
        'receiver_id': receiver_id,
        'message_text': message_text,
        'sender_name': sender.username,
        'timestamp': new_message.timestamp.strftime('%H:%M')
    }, room=receiver_id)
    # Also emit to sender's room to update their UI
    socketio.emit('receive_message', {
        'sender_id': current_user.custom_id,
        'receiver_id': receiver_id,
        'message_text': message_text,
        'sender_name': sender.username,
        'timestamp': new_message.timestamp.strftime('%H:%M')
    }, room=current_user.custom_id)

    return jsonify({'success': True, 'message': 'Message sent successfully'}), 201

@message_bp.route('/chat')
@login_required
def chat_page():
    return render_template('chat.html', current_user=current_user)

@message_bp.route('/api/messages/<receiver_id>', methods=['GET'])
@login_required
def get_messages(receiver_id):
    messages = Messages.query.filter(
        ((Messages.sender_id == current_user.custom_id) & (Messages.receiver_id == receiver_id)) |
        ((Messages.sender_id == receiver_id) & (Messages.receiver_id == current_user.custom_id))
    ).order_by(Messages.timestamp).all()

    chat_data = [{
        'sender_id': msg.sender_id,
        'message_text': msg.message_text,
        'timestamp': msg.timestamp.strftime('%H:%M')
    } for msg in messages]

    return jsonify(chat_data)

@message_bp.route('/api/mark_as_read/<sender_id>', methods=['POST'])
@login_required
def mark_as_read(sender_id):
    # Mark all messages from this sender as read
    Messages.query.filter_by(
        sender_id=sender_id,
        receiver_id=current_user.custom_id,
        is_read=False
    ).update({'is_read': True})
    db.session.commit()
    return jsonify({'success': True})