from flask import Blueprint, render_template, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import Users, Messages, Groups
from extensions import db, socketio

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('index'))

    users = Users.query.all()
    messages = Messages.query.all()
    groups = Groups.query.all()
    online_users_count = Users.query.filter_by(is_online=True).count()

    return render_template('admin.html', users=users, messages=messages, groups=groups, online_users_count=online_users_count)

@admin_bp.route('/admin/delete_user/<user_id>', methods=['DELETE'])
@login_required
def admin_delete_user(user_id):
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403
    user = Users.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    db.session.delete(user)
    db.session.commit()
    return jsonify({"success": True, "message": "User deleted successfully!"}), 200

@admin_bp.route('/admin/delete_message/<message_id>', methods=['DELETE'])
@login_required
def admin_delete_message(message_id):
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403
    from models import Messages
    message = Messages.query.get(message_id)
    if not message:
        return jsonify({"error": "Message not found"}), 404
    db.session.delete(message)
    db.session.commit()
    return jsonify({"success": True, "message": "Message deleted successfully!"}), 200

@admin_bp.route('/admin/view_user/<user_id>')
@login_required
def admin_view_user(user_id):
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403
    user = Users.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return render_template('view_user.html', user=user)
