from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user
from models import User, Project, ProjectMembership, ProjectRequest
from extensions import db

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def _admin_only():
    if not current_user.is_admin():
        abort(403)


@admin_bp.route('/')
@login_required
def index():
    _admin_only()
    users = User.query.order_by(User.role, User.full_name).all()
    projects = Project.query.order_by(Project.created_at.desc()).all()
    requests = ProjectRequest.query.order_by(ProjectRequest.created_at.desc()).all()
    return render_template('admin/index.html', users=users, projects=projects, requests=requests)


@admin_bp.route('/users/new', methods=['GET', 'POST'])
@login_required
def new_user():
    _admin_only()
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()
        role = request.form.get('role', 'employee')
        email = request.form.get('email', '').strip()
        if not username or not password or not full_name:
            flash('Username, password, and name are required.', 'danger')
            return render_template('admin/new_user.html')
        if User.query.filter_by(username=username).first():
            flash('Username taken.', 'danger')
            return render_template('admin/new_user.html')
        u = User(username=username, full_name=full_name, role=role, email=email or None)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        flash(f'User "{username}" created.', 'success')
        return redirect(url_for('admin.index'))
    return render_template('admin/new_user.html')


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    _admin_only()
    if user_id == current_user.id:
        flash('Cannot delete your own account.', 'danger')
        return redirect(url_for('admin.index'))
    u = User.query.get_or_404(user_id)
    db.session.delete(u)
    db.session.commit()
    flash('User deleted.', 'success')
    return redirect(url_for('admin.index'))


@admin_bp.route('/projects/<int:project_id>/members', methods=['POST'])
@login_required
def assign_members(project_id):
    _admin_only()
    p = Project.query.get_or_404(project_id)
    user_ids = request.form.getlist('user_ids', type=int)
    for uid in user_ids:
        if not ProjectMembership.query.filter_by(project_id=project_id, user_id=uid).first():
            db.session.add(ProjectMembership(project_id=project_id, user_id=uid))
    db.session.commit()
    flash('Members updated.', 'success')
    return redirect(url_for('admin.index'))
