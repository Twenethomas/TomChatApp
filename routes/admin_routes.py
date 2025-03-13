import csv
import io
from flask import Blueprint, current_app, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from werkzeug import Response
from models import Users, Messages, Groups
from extensions import db, socketio
from flask_socketio import emit
from datetime import datetime

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        return redirect(url_for('message.chat_page'))

    page = request.args.get('page', 1, type=int)
    per_page = 10

    users = Users.query.order_by(Users.custom_id).paginate(page=page, per_page=per_page, error_out=False)
    messages = Messages.query.order_by(Messages.timestamp.desc()).paginate(page=page, per_page=per_page, error_out=False)
    groups = Groups.query.order_by(Groups.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    return render_template('admin.html', users=users, messages=messages, groups=groups)


@admin_bp.route('/admin/delete_user/<user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    """Delete a user and update dashboard."""
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    user = Users.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    db.session.delete(user)
    db.session.commit()
    return jsonify({"success": True, "message": "User deleted successfully!"})

@admin_bp.route('/admin/block_user/<user_id>', methods=['POST'])
@login_required
def block_user(user_id):
    """Block or Unblock a user."""
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    user = Users.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    user.is_blocked = not user.is_blocked
    db.session.commit()
    return jsonify({"success": True, "message": f"User {'blocked' if user.is_blocked else 'unblocked'} successfully!"})
@admin_bp.route('/admin/get_users')
@login_required
def get_users():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    users = Users.query.order_by(Users.custom_id).paginate(page=page, per_page=per_page, error_out=False)

    users_data = [{
        "id": user.custom_id,
        "username": user.username,
        "is_online": user.is_online,
        "last_seen": user.last_seen.strftime('%Y-%m-%d %H:%M:%S') if user.last_seen else "Never"
    } for user in users.items]

    return jsonify({
        "users": users_data,
        "total_pages": users.pages,
        "current_page": users.page
    })

@admin_bp.route('/admin/get_groups')
@login_required
def get_groups():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    groups = Groups.query.order_by(Groups.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    groups_data = [{
        "id": group.custom_id,
        "group_name": group.group_name,
        "created_by": group.created_by,
        "created_at": group.created_at.strftime('%Y-%m-%d %H:%M:%S')
    } for group in groups.items]

    return jsonify({
        "groups": groups_data,
        "total_pages": groups.pages,
        "current_page": groups.page
    })

@admin_bp.route('/admin/get_messages')
@login_required
def get_messages():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    messages = Messages.query.order_by(Messages.timestamp.desc()).paginate(page=page, per_page=per_page, error_out=False)

    messages_data = [{
        "id": message.custom_id,
        "sender_id": message.sender_id,
        "receiver_id": message.receiver_id,
        "message_text": message.message_text,
        "timestamp": message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    } for message in messages.items]

    return jsonify({
        "messages": messages_data,
        "total_pages": messages.pages,
        "current_page": messages.page
    })


def emit_dashboard_statistics():
    """Emit real-time statistics and data to all connected admins."""
    total_users = Users.query.count()
    online_users_count = Users.query.filter_by(is_online=True).count()
    total_messages = Messages.query.count()
    total_groups = Groups.query.count()

    users = Users.query.all()
    groups = Groups.query.all()
    messages = Messages.query.order_by(Messages.timestamp.desc()).all()

    socketio.emit('update_dashboard', {
        'total_users': total_users,
        'online_users_count': online_users_count,
        'total_messages': total_messages,
        'total_groups': total_groups,
        'users': [{'id': u.custom_id, 'username': u.username, 'is_online': u.is_online, 'last_seen': str(u.last_seen) if u.last_seen else "Never"} for u in users],
        'groups': [{'id': g.custom_id, 'group_name': g.group_name, 'created_by': g.created_by} for g in groups],
        'messages': [{'id': m.custom_id, 'sender_id': m.sender_id, 'receiver_id': m.receiver_id, 'message_text': m.message_text, 'timestamp': str(m.timestamp)} for m in messages]
    }, namespace='/admin')

@socketio.on('connect', namespace='/admin')
def handle_admin_connect():
    emit_dashboard_statistics()

@admin_bp.route('/admin/add_user', methods=['POST'])
@login_required
def add_user():
    """Add a new user and update the dashboard."""
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    new_user = Users(username=data['username'], password=data['password'])
    db.session.add(new_user)
    db.session.commit()

    emit_dashboard_statistics()
    return jsonify({"success": True, "message": "User added successfully!"})

@admin_bp.route('/admin/add_group', methods=['POST'])
@login_required
def add_group():
    """Add a new group and update the dashboard."""
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    new_group = Groups(group_name=data['group_name'], created_by=current_user.custom_id)
    db.session.add(new_group)
    db.session.commit()

    emit_dashboard_statistics()
    return jsonify({"success": True, "message": "Group added successfully!"})

@admin_bp.route('/admin/add_message', methods=['POST'])
@login_required
def add_message():
    """Add a new message and update the dashboard."""
    data = request.json
    new_message = Messages(sender_id=data['sender_id'], receiver_id=data['receiver_id'], message_text=data['message_text'])
    db.session.add(new_message)
    db.session.commit()

    emit_dashboard_statistics()
    return jsonify({"success": True, "message": "Message sent successfully!"})


@admin_bp.route('/admin/view_user/<user_id>', methods=['GET'])
@login_required
def view_user(user_id):
    """Fetch details of a specific user."""
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    user = Users.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "id": user.custom_id,
        "username": user.username,
        "status": user.status,
        "is_online": user.is_online,
        "is_blocked": user.is_blocked,
        "last_seen": str(user.last_seen) if user.last_seen else "Never",
        "profile_picture": user.profile_picture
    })


# 1. Delete Group Route
@admin_bp.route('/admin/delete_group/<group_id>', methods=['DELETE'])
@login_required
def delete_group(group_id):
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    group = Groups.query.get(group_id)
    if not group:
        return jsonify({"error": "Group not found"}), 404

    db.session.delete(group)
    db.session.commit()
    emit_dashboard_statistics()
    return jsonify({"success": True, "message": "Group deleted successfully!"})

# 2. Delete Message Route
@admin_bp.route('/admin/delete_message/<message_id>', methods=['DELETE'])
@login_required
def delete_message(message_id):
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    message = Messages.query.get(message_id)
    if not message:
        return jsonify({"error": "Message not found"}), 404

    db.session.delete(message)
    db.session.commit()
    emit_dashboard_statistics()
    return jsonify({"success": True, "message": "Message deleted successfully!"})

# 3. Edit User Route
@admin_bp.route('/admin/edit_user/<user_id>', methods=['PUT'])
@login_required
def edit_user(user_id):
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    user = Users.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.json
    if 'username' in data:
        user.username = data['username']
    if 'password' in data:
        user.set_password(data['password'])
    if 'status' in data:
        user.status = data['status']
    
    db.session.commit()
    emit_dashboard_statistics()
    return jsonify({"success": True, "message": "User updated successfully!"})

# 4. Edit Group Route
@admin_bp.route('/admin/edit_group/<group_id>', methods=['PUT'])
@login_required
def edit_group(group_id):
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    group = Groups.query.get(group_id)
    if not group:
        return jsonify({"error": "Group not found"}), 404

    data = request.json
    if 'group_name' in data:
        group.group_name = data['group_name']
    
    db.session.commit()
    emit_dashboard_statistics()
    return jsonify({"success": True, "message": "Group updated successfully!"})

# 5. Search Users
@admin_bp.route('/admin/search_users')
@login_required
def search_users():
    search_query = request.args.get('query', '')
    page = request.args.get('page', 1, type=int)
    per_page = 10

    users = Users.query.filter(Users.username.ilike(f'%{search_query}%'))\
        .order_by(Users.custom_id)\
        .paginate(page=page, per_page=per_page, error_out=False)

    users_data = [{
        "id": user.custom_id,
        "username": user.username,
        "is_online": user.is_online,
        "last_seen": user.last_seen.strftime('%Y-%m-%d %H:%M:%S') if user.last_seen else "Never"
    } for user in users.items]

    return jsonify({
        "users": users_data,
        "total_pages": users.pages,
        "current_page": users.page
    })

# 6. Export Users as CSV
@admin_bp.route('/admin/export_users')
@login_required
def export_users():
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    users = Users.query.all()
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['ID', 'Username', 'Status', 'Last Seen', 'Blocked'])
    
    # Write data
    for user in users:
        writer.writerow([
            user.custom_id,
            user.username,
            user.status,
            user.last_seen.strftime('%Y-%m-%d %H:%M:%S') if user.last_seen else 'Never',
            user.is_blocked
        ])
    
    output.seek(0)
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=users_export.csv"}
    )

# 7. Bulk Delete Users
@admin_bp.route('/admin/bulk_delete_users', methods=['POST'])
@login_required
def bulk_delete_users():
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    user_ids = request.json.get('user_ids', [])
    Users.query.filter(Users.custom_id.in_(user_ids)).delete(synchronize_session=False)
    db.session.commit()
    emit_dashboard_statistics()
    return jsonify({"success": True, "message": f"{len(user_ids)} users deleted successfully!"})

# 8. Promote/Demote Admin
@admin_bp.route('/admin/set_admin_status/<user_id>', methods=['POST'])
@login_required
def set_admin_status(user_id):
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    user = Users.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    user.is_admin = not user.is_admin
    db.session.commit()
    return jsonify({
        "success": True,
        "message": f"User {'promoted to admin' if user.is_admin else 'demoted from admin'} successfully!"
    })

# 9. Message Filtering
@admin_bp.route('/admin/filter_messages')
@login_required
def filter_messages():
    search_query = request.args.get('query', '')
    page = request.args.get('page', 1, type=int)
    per_page = 10

    messages = Messages.query.filter(Messages.message_text.ilike(f'%{search_query}%'))\
        .order_by(Messages.timestamp.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    messages_data = [{
        "id": message.custom_id,
        "sender_id": message.sender_id,
        "receiver_id": message.receiver_id,
        "message_text": message.message_text,
        "timestamp": message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    } for message in messages.items]

    return jsonify({
        "messages": messages_data,
        "total_pages": messages.pages,
        "current_page": messages.page
    })

# 10. System Settings (Example)
@admin_bp.route('/admin/system_settings', methods=['GET', 'POST'])
@login_required
def system_settings():
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    if request.method == 'POST':
        data = request.json
        # Example setting - would typically store in database
        current_app.config['MAX_USERS'] = data.get('max_users', 1000)
        return jsonify({"success": True, "message": "Settings updated successfully!"})
    
    return jsonify({
        "max_users": current_app.config.get('MAX_USERS', 1000),
        "message_retention_days": current_app.config.get('MESSAGE_RETENTION_DAYS', 30)
    })