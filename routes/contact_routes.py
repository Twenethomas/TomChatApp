from flask import Blueprint, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import Users, Contacts
from extensions import db

contact_bp = Blueprint('contact', __name__)

@contact_bp.route('/contacts', methods=['GET'])
@login_required
def get_contacts():
    contacts = Contacts.query.filter_by(user_id=current_user.custom_id).all()
    contacts_data = [
        {
            'contact_id': contact.custom_id,
            'username': contact.contact_user.username,
            'status': contact.contact_user.status,
            'last_seen': contact.contact_user.last_seen.strftime('%Y-%m-%d %H:%M:%S') if contact.contact_user.last_seen else None
        }
        for contact in contacts
    ]
    return jsonify(contacts_data)