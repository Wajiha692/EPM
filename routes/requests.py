from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user
from datetime import datetime
from models import User, Project, ProjectMembership, ProjectRequest
from extensions import db

requests_bp = Blueprint('requests', __name__)


@requests_bp.route('/requests/new', methods=['GET', 'POST'])
@login_required
def new_request():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        if not title:
            flash('Title is required.', 'danger')
            return render_template('requests/new.html')
        deadline_str = request.form.get('deadline', '')
        deadline = None
        if deadline_str:
            try: deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
            except: pass
        req = ProjectRequest(
            title=title,
            description=request.form.get('description', '').strip(),
            priority=request.form.get('priority', 'medium'),
            deadline=deadline,
            estimated_hours=request.form.get('estimated_hours', type=int),
            requested_by=current_user.id
        )
        db.session.add(req)
        db.session.commit()
        flash('Your project request has been submitted!', 'success')
        return redirect(url_for('projects.list_projects'))
    return render_template('requests/new.html')


@requests_bp.route('/requests/<int:req_id>')
@login_required
def detail(req_id):
    req = ProjectRequest.query.get_or_404(req_id)
    if not current_user.is_manager() and req.requested_by != current_user.id:
        abort(403)
    employees = User.query.filter(User.role.in_(['employee', 'manager'])).order_by(User.full_name).all()
    return render_template('requests/detail.html', req=req, employees=employees)


@requests_bp.route('/requests/<int:req_id>/approve', methods=['POST'])
@login_required
def approve(req_id):
    if not current_user.is_manager():
        abort(403)
    req = ProjectRequest.query.get_or_404(req_id)
    member_ids = request.form.getlist('members', type=int)
    if not member_ids:
        flash('Select at least one member.', 'danger')
        return redirect(url_for('requests.detail', req_id=req_id))

    # Create project from request
    p = Project(
        name=req.title, description=req.description,
        priority=req.priority, deadline=req.deadline,
        estimated_hours=req.estimated_hours,
        created_by=current_user.id, status='active'
    )
    db.session.add(p)
    db.session.flush()

    # Add members including requester
    all_ids = set(member_ids) | {req.requested_by, current_user.id}
    for uid in all_ids:
        if User.query.get(uid):
            db.session.add(ProjectMembership(project_id=p.id, user_id=uid))

    req.status = 'approved'
    req.reviewed_by = current_user.id
    req.project_id = p.id
    db.session.commit()
    flash(f'Request approved! Project "{p.name}" is now active.', 'success')
    return redirect(url_for('projects.workspace', project_id=p.id))


@requests_bp.route('/requests/<int:req_id>/reject', methods=['POST'])
@login_required
def reject(req_id):
    if not current_user.is_manager():
        abort(403)
    req = ProjectRequest.query.get_or_404(req_id)
    req.status = 'rejected'
    req.reviewed_by = current_user.id
    req.rejection_reason = request.form.get('reason', '').strip()
    db.session.commit()
    flash('Request rejected.', 'warning')
    return redirect(url_for('projects.list_projects'))
