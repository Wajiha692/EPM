from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user
from datetime import datetime
from models import User, Project, ProjectMembership, ProjectRequest
from extensions import db

projects_bp = Blueprint('projects', __name__)


def _get_project_or_403(project_id):
    p = Project.query.get_or_404(project_id)
    if not current_user.is_manager() and not current_user.is_member_of(project_id):
        abort(403)
    return p


@projects_bp.route('/projects')
@login_required
def list_projects():
    q = request.args.get('q', '').strip()
    status_f = request.args.get('status', 'all')

    if current_user.is_manager():
        query = Project.query
    else:
        ids = [m.project_id for m in current_user.memberships.all()]
        query = Project.query.filter(Project.id.in_(ids))

    if q:
        query = query.filter(Project.name.ilike(f'%{q}%'))
    if status_f != 'all':
        query = query.filter_by(status=status_f)

    projects = query.order_by(Project.created_at.desc()).all()

    # Pending requests for manager/admin
    pending_requests = []
    if current_user.is_manager():
        pending_requests = ProjectRequest.query.filter_by(status='pending').all()

    # My notifications (approved/rejected requests)
    my_notifications = []
    if current_user.role == 'employee':
        my_notifications = ProjectRequest.query.filter_by(
            requested_by=current_user.id
        ).filter(ProjectRequest.status.in_(['approved', 'rejected'])).order_by(
            ProjectRequest.updated_at.desc()
        ).limit(5).all()

    return render_template('projects/list.html',
        projects=projects, q=q, status_f=status_f,
        pending_requests=pending_requests,
        my_notifications=my_notifications)


@projects_bp.route('/projects/new', methods=['GET', 'POST'])
@login_required
def new_project():
    if not current_user.is_manager():
        abort(403)
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('Project name is required.', 'danger')
            return render_template('projects/new.html', users=User.query.all())

        from datetime import date
        deadline_str = request.form.get('deadline', '')
        deadline = None
        if deadline_str:
            try: deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
            except: pass

        p = Project(
            name=name,
            description=request.form.get('description', '').strip(),
            priority=request.form.get('priority', 'medium'),
            deadline=deadline,
            estimated_hours=request.form.get('estimated_hours', type=int),
            created_by=current_user.id, status='active'
        )
        db.session.add(p)
        db.session.flush()

        # Add selected members
        member_ids = request.form.getlist('members', type=int)
        if current_user.id not in member_ids:
            member_ids.append(current_user.id)
        for uid in member_ids:
            if User.query.get(uid):
                db.session.add(ProjectMembership(project_id=p.id, user_id=uid))
        db.session.commit()
        flash(f'Project "{name}" created!', 'success')
        return redirect(url_for('projects.workspace', project_id=p.id))

    return render_template('projects/new.html', users=User.query.order_by(User.full_name).all())


@projects_bp.route('/projects/<int:project_id>')
@login_required
def workspace(project_id):
    p = _get_project_or_403(project_id)
    from datetime import date
    today = date.today()
    tasks = p.tasks.all()
    todo = [t for t in tasks if t.status == 'todo']
    in_prog = [t for t in tasks if t.status == 'in_progress']
    done = [t for t in tasks if t.status == 'done']
    overdue = [t for t in tasks if t.is_overdue]
    recent = sorted(tasks, key=lambda t: t.updated_at, reverse=True)[:6]
    members = p.get_members()
    return render_template('projects/workspace.html',
        p=p, todo=todo, in_prog=in_prog, done=done,
        overdue=overdue, recent=recent, members=members, today=today)
