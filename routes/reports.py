from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
from models import Project, Task, User
from extensions import db
from sqlalchemy import func
from datetime import date
import json

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/projects/<int:project_id>/reports')
@login_required
def index(project_id):
    p = Project.query.get_or_404(project_id)
    if not current_user.is_manager() and not current_user.is_member_of(project_id):
        abort(403)

    today = date.today()
    tasks = p.tasks.all()

    # Status counts
    status_counts = {'todo': 0, 'in_progress': 0, 'done': 0}
    for t in tasks:
        status_counts[t.status] = status_counts.get(t.status, 0) + 1

    # Tasks per member
    members = p.get_members()
    per_member = []
    for m in members:
        mt = [t for t in tasks if t.assigned_to == m.id]
        per_member.append({
            'name': m.full_name,
            'todo': sum(1 for t in mt if t.status == 'todo'),
            'in_progress': sum(1 for t in mt if t.status == 'in_progress'),
            'done': sum(1 for t in mt if t.status == 'done'),
        })

    overdue_tasks = [t for t in tasks if t.is_overdue]

    # Priority breakdown
    priority_counts = {'high': 0, 'medium': 0, 'low': 0}
    for t in tasks:
        priority_counts[t.priority] = priority_counts.get(t.priority, 0) + 1

    chart_status = json.dumps(status_counts)
    chart_members = json.dumps(per_member)
    chart_priority = json.dumps(priority_counts)

    return render_template('projects/reports.html',
        p=p, tasks=tasks, status_counts=status_counts,
        per_member=per_member, overdue_tasks=overdue_tasks,
        priority_counts=priority_counts,
        chart_status=chart_status,
        chart_members=chart_members,
        chart_priority=chart_priority)
