from flask import Blueprint, render_template, request, jsonify, abort
from flask_login import login_required, current_user
from models import Project, ChatMessage
from extensions import db

chat_bp = Blueprint('chat', __name__)


def _check_access(project_id):
    p = Project.query.get_or_404(project_id)
    if not current_user.is_manager() and not current_user.is_member_of(project_id):
        abort(403)
    return p


@chat_bp.route('/projects/<int:project_id>/chat')
@login_required
def index(project_id):
    p = _check_access(project_id)
    messages = ChatMessage.query.filter_by(project_id=project_id)\
        .order_by(ChatMessage.created_at.desc()).limit(100).all()
    messages = list(reversed(messages))
    return render_template('projects/chat.html', p=p, messages=messages)


@chat_bp.route('/projects/<int:project_id>/chat/send', methods=['POST'])
@login_required
def send(project_id):
    _check_access(project_id)
    body = request.form.get('body', '').strip()
    if body and len(body) <= 1000:
        db.session.add(ChatMessage(body=body, project_id=project_id, user_id=current_user.id))
        db.session.commit()
    return ('', 204)


@chat_bp.route('/projects/<int:project_id>/chat/messages')
@login_required
def messages_api(project_id):
    _check_access(project_id)
    since = request.args.get('since', 0, type=int)
    msgs = ChatMessage.query.filter(ChatMessage.project_id == project_id, ChatMessage.id > since)\
        .order_by(ChatMessage.created_at.asc()).limit(50).all()
    return jsonify([{
        'id': m.id, 'body': m.body,
        'username': m.sender.username, 'full_name': m.sender.full_name,
        'initials': m.sender.avatar_initials, 'role': m.sender.role,
        'time': m.created_at.strftime('%H:%M'), 'mine': m.user_id == current_user.id
    } for m in msgs])
