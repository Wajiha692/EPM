from flask import Blueprint, render_template, redirect, url_for, request, flash, abort, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from models import Project, Task, Comment, ProjectMembership, User
from extensions import db

tasks_bp = Blueprint('tasks', __name__)


def _check_project_access(project_id):
    p = Project.query.get_or_404(project_id)
    if not current_user.is_manager() and not current_user.is_member_of(project_id):
        abort(403)
    return p


@tasks_bp.route('/projects/<int:project_id>/board')
@login_required
def board(project_id):
    p = _check_project_access(project_id)
    tasks = p.tasks.all()
    todo     = sorted([t for t in tasks if t.status == 'todo'],        key=lambda t: t.priority == 'high', reverse=True)
    in_prog  = sorted([t for t in tasks if t.status == 'in_progress'], key=lambda t: t.priority == 'high', reverse=True)
    done     = sorted([t for t in tasks if t.status == 'done'],        key=lambda t: t.updated_at, reverse=True)
    members  = p.get_members()
    return render_template('projects/board.html',
        p=p, todo=todo, in_prog=in_prog, done=done, members=members)


@tasks_bp.route('/projects/<int:project_id>/tasks/new', methods=['GET', 'POST'])
@login_required
def new_task(project_id):
    if not current_user.is_manager():
        abort(403)
    p = Project.query.get_or_404(project_id)
    members = p.get_members()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        assigned_to = request.form.get('assigned_to', type=int)
        if not title or not assigned_to:
            flash('Title and assignee are required.', 'danger')
            return render_template('projects/new_task.html', p=p, members=members)
        deadline_str = request.form.get('deadline', '')
        deadline = None
        if deadline_str:
            try: deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
            except: pass
        t = Task(
            title=title,
            description=request.form.get('description', '').strip(),
            priority=request.form.get('priority', 'medium'),
            deadline=deadline,
            project_id=project_id,
            assigned_to=assigned_to,
            created_by=current_user.id
        )
        db.session.add(t)
        db.session.commit()
        flash('Task created!', 'success')
        return redirect(url_for('tasks.board', project_id=project_id))
    return render_template('projects/new_task.html', p=p, members=members)


@tasks_bp.route('/projects/<int:project_id>/tasks/<int:task_id>')
@login_required
def task_detail(project_id, task_id):
    p = _check_project_access(project_id)
    t = Task.query.get_or_404(task_id)
    if t.project_id != project_id:
        abort(404)
    comments = t.comments.order_by(Comment.created_at.asc()).all()
    members = p.get_members()
    return render_template('projects/task_detail.html', p=p, t=t, comments=comments, members=members)


@tasks_bp.route('/projects/<int:project_id>/tasks/<int:task_id>/status', methods=['POST'])
@login_required
def update_status(project_id, task_id):
    _check_project_access(project_id)
    t = Task.query.get_or_404(task_id)
    if t.project_id != project_id:
        abort(404)
    if not current_user.is_manager() and t.assigned_to != current_user.id:
        abort(403)
    new_status = request.form.get('status')
    if new_status in ('todo', 'in_progress', 'done'):
        t.status = new_status
        t.updated_at = datetime.utcnow()
        db.session.commit()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'ok': True, 'status': new_status})
        flash('Status updated.', 'success')
    return redirect(url_for('tasks.board', project_id=project_id))


@tasks_bp.route('/projects/<int:project_id>/tasks/<int:task_id>/comment', methods=['POST'])
@login_required
def add_comment(project_id, task_id):
    _check_project_access(project_id)
    t = Task.query.get_or_404(task_id)
    body = request.form.get('body', '').strip()
    if body:
        db.session.add(Comment(body=body, task_id=task_id, user_id=current_user.id))
        db.session.commit()
    return redirect(url_for('tasks.task_detail', project_id=project_id, task_id=task_id))


@tasks_bp.route('/projects/<int:project_id>/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(project_id, task_id):
    if not current_user.is_manager():
        abort(403)
    t = Task.query.get_or_404(task_id)
    db.session.delete(t)
    db.session.commit()
    flash('Task deleted.', 'success')
    return redirect(url_for('tasks.board', project_id=project_id))
