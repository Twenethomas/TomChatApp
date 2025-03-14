from datetime import datetime, timedelta
import csv
import io
from flask import Blueprint, current_app, render_template, request, jsonify, redirect, url_for, Response
from flask_login import login_required, current_user
from sqlalchemy import func, text
from models import Settings, Users, Messages, Groups
from extensions import db, socketio
from flask_socketio import emit

admin_bp = Blueprint('admin', __name__)

# ----------------------
# Data Aggregation Functions
# ----------------------
from sqlalchemy import text

def get_online_time_distribution():
    """Get hourly distribution of online users (SQL Server compatible)"""
    distribution = [0] * 24
    # Use raw SQL for DATEPART with literal 'hour'
    results = db.session.query(
        text("DATEPART(hour, users.last_seen) AS hour"),
        func.count(Users.custom_id)
    ).filter(
        Users.is_online == True
    ).group_by(
        text("DATEPART(hour, users.last_seen)")  # Group by the same expression
    ).all()
    
    for hour, count in results:
        distribution[hour] = count
    return distribution
def get_message_activity():
    """Get message counts for last 24 hours"""
    now = datetime.utcnow()
    message_activity = []
    
    for i in range(24):
        hour_start = now - timedelta(hours=i)
        hour_end = hour_start + timedelta(hours=1)
        count = Messages.query.filter(
            Messages.timestamp.between(hour_start, hour_end)
        ).count()
        message_activity.append({
            "hour": hour_start.strftime("%H:%M"),
            "count": count
        })
    
    return message_activity[::-1]  # Reverse to show oldest first

def get_user_activity_heatmap():
    """Get weekly activity (SQL Server compatible)"""
    activity = [0] * 7  # 0=Monday, 6=Sunday
    for i in range(7):
        target_dw = (i + 1) % 7 + 1  # Map to SQL Server dw (1=Sunday)
        count = Users.query.filter(
            text("DATEPART(dw, users.last_seen) = :target_dw")
        ).params(target_dw=target_dw).count()
        activity[i] = count
    return activity

# ----------------------
# Core Routes
# ----------------------

@admin_bp.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        return redirect(url_for('message.chat_page'))

    return render_template('admin.html')

@admin_bp.route('/admin/initial_data')
@login_required
def initial_data():
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        data = {
            'total_users': Users.query.count(),
            'online_users_count': Users.query.filter_by(is_online=True).count(),
            'total_messages': Messages.query.count(),
            'total_groups': Groups.query.count(),
            'daily_messages': Messages.query.filter(
                Messages.timestamp >= datetime.utcnow() - timedelta(hours=24)
            ).count(),
            'active_groups': Groups.query.filter(
                Groups.created_at >= datetime.utcnow() - timedelta(days=7)
            ).count(),
            'online_time_distribution': get_online_time_distribution(),
            'message_activity': get_message_activity(),
            'user_activity_heatmap': get_user_activity_heatmap()
        }
        return jsonify(data)
    
    except Exception as e:
        current_app.logger.error(f"Error in initial_data: {str(e)}")
        return jsonify({"error": "Server error"}), 500

# ----------------------
# Real-time Updates
# ----------------------

def emit_dashboard_statistics():
    """Emit comprehensive real-time statistics"""
    data = {
        'total_users': Users.query.count(),
        'online_users_count': Users.query.filter_by(is_online=True).count(),
        'total_messages': Messages.query.count(),
        'total_groups': Groups.query.count(),
        'daily_messages': Messages.query.filter(
            Messages.timestamp >= datetime.utcnow() - timedelta(hours=24)
        ).count(),
        'active_groups': Groups.query.filter(
            Groups.created_at >= datetime.utcnow() - timedelta(days=7)
        ).count(),
        'online_time_distribution': get_online_time_distribution(),
        'message_activity': get_message_activity(),
        'user_activity_heatmap': get_user_activity_heatmap()
    }
    socketio.emit('update_dashboard', data, namespace='/admin')

@socketio.on('connect', namespace='/admin')
def handle_admin_connect():
    emit_dashboard_statistics()

# ----------------------
# CRUD Operations (Keep only one version of each)
# ----------------------

@admin_bp.route('/admin/delete_user/<user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    user = Users.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    db.session.delete(user)
    db.session.commit()
    emit_dashboard_statistics()
    return jsonify({"success": True, "message": "User deleted successfully!"})

# ... Keep other CRUD operations but remove duplicates ...

# Users Route with Search/Pagination
@admin_bp.route('/admin/get_users')
@login_required
def get_users():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('query', '')
    
    base_query = Users.query
    if search_query:
        base_query = base_query.filter(Users.username.ilike(f'%{search_query}%'))
    
    users = base_query.order_by(Users.username).paginate(page=page, per_page=10, error_out=False)
    
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

# Messages Route with Search/Pagination
@admin_bp.route('/admin/get_messages')
@login_required
def get_messages():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('query', '')
    
    base_query = Messages.query
    if search_query:
        base_query = base_query.filter(Messages.message_text.ilike(f'%{search_query}%'))
    
    messages = base_query.order_by(Messages.timestamp.desc()).paginate(page=page, per_page=10, error_out=False)
    
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

# Groups Route with Search/Pagination
@admin_bp.route('/admin/get_groups')
@login_required
def get_groups():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('query', '')
    
    base_query = Groups.query
    if search_query:
        base_query = base_query.filter(Groups.group_name.ilike(f'%{search_query}%'))
    
    groups = base_query.order_by(Groups.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
    
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

@admin_bp.route('/admin/toggle_view', methods=['POST'])
@login_required
def toggle_view():
    return jsonify({
        "show_charts": not request.json.get('show_tables', False)
    })
@admin_bp.route('/admin/get_settings')
@login_required
def get_settings():
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('query', '')
    
    base_query = Settings.query
    if search_query:
        base_query = base_query.filter(
            Settings.key.ilike(f'%{search_query}%') |
            Settings.value.ilike(f'%{search_query}%')
        )
    
    settings = base_query.order_by(Settings.key).paginate(page=page, per_page=10, error_out=False)
    
    settings_data = [{
        "id": setting.custom_id,
        "key": setting.key,
        "value": setting.value,
        "description": setting.description,
        "last_modified": setting.last_modified.strftime('%Y-%m-%d %H:%M:%S')
    } for setting in settings.items]

    return jsonify({
        "settings": settings_data,
        "total_pages": settings.pages,
        "current_page": settings.page
    })

# Add to admin_routes.py
@admin_bp.route('/admin/update_setting/<setting_id>', methods=['PUT'])
@login_required
def update_setting(setting_id):
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    setting = Settings.query.get(setting_id)
    if not setting:
        return jsonify({"error": "Setting not found"}), 404

    data = request.json
    if 'value' in data:
        setting.value = data['value']
    if 'description' in data:
        setting.description = data['description']
    
    db.session.commit()
    return jsonify({"success": True, "message": "Setting updated successfully!"})

@admin_bp.route('/admin/delete_setting/<setting_id>', methods=['DELETE'])
@login_required
def delete_setting(setting_id):
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403

    setting = Settings.query.get(setting_id)
    if not setting:
        return jsonify({"error": "Setting not found"}), 404

    db.session.delete(setting)
    db.session.commit()
    return jsonify({"success": True, "message": "Setting deleted successfully!"})