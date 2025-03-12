from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import Groups, GroupMembers
from extensions import db, socketio

group_bp = Blueprint('group', __name__)

@group_bp.route('/group/create', methods=['POST'])
@login_required
def create_group():
    data = request.get_json()
    group_name = data.get('group_name')

    if not group_name:
        return jsonify({'error': 'Group name required'}), 400

    new_group = Groups(group_name=group_name, created_by=current_user.custom_id)
    db.session.add(new_group)
    db.session.commit()

    # Add the creator as a member
    new_member = GroupMembers(group_id=new_group.custom_id, user_id=current_user.custom_id)
    db.session.add(new_member)
    db.session.commit()

    return jsonify({'success': True, 'group_id': new_group.custom_id}), 201
