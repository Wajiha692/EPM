import os
from flask import Flask, render_template
from extensions import db, login_manager
from config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    login_manager.init_app(app)

    from routes.auth import auth_bp
    from routes.projects import projects_bp
    from routes.tasks import tasks_bp
    from routes.chat import chat_bp
    from routes.reports import reports_bp
    from routes.requests import requests_bp
    from routes.admin import admin_bp

    for bp in [auth_bp, projects_bp, tasks_bp, chat_bp, reports_bp, requests_bp, admin_bp]:
        app.register_blueprint(bp)

    @app.errorhandler(403)
    def forbidden(e): return render_template('error.html', code=403, msg='Access Forbidden'), 403

    @app.errorhandler(404)
    def not_found(e): return render_template('error.html', code=404, msg='Page Not Found'), 404

    with app.app_context():
        db.create_all()
        _seed()

    return app


def _seed():
    from models import User, Project, ProjectMembership, ProjectRequest, Task, ChatMessage
    from datetime import date, timedelta

    if User.query.count():
        return  # already seeded

    # ── Users ──────────────────────────────────────────────────────
    def make_user(username, pw, role, full_name, email):
        u = User(username=username, role=role, full_name=full_name, email=email)
        u.set_password(pw)
        db.session.add(u)
        return u

    admin   = make_user('admin',     'admin123',    'admin',    'Alex Admin',     'admin@co.com')
    manager = make_user('manager',   'manager123',  'manager',  'Morgan Manager', 'manager@co.com')
    emp1    = make_user('employee1', 'emp123',      'employee', 'Emma Employee',  'emma@co.com')
    emp2    = make_user('employee2', 'emp456',      'employee', 'Evan Employee',  'evan@co.com')
    db.session.flush()

    # ── Projects ────────────────────────────────────────────────────
    today = date.today()

    p1 = Project(name='Website Redesign', description='Full redesign of the company website with modern UI and improved UX.',
                 status='active', priority='high', deadline=today + timedelta(days=30),
                 estimated_hours=120, created_by=manager.id)
    p2 = Project(name='Mobile App MVP', description='Build the first version of our customer-facing mobile application.',
                 status='active', priority='medium', deadline=today + timedelta(days=60),
                 estimated_hours=200, created_by=admin.id)
    db.session.add_all([p1, p2])
    db.session.flush()

    # memberships
    for uid in [manager.id, emp1.id, emp2.id]:
        db.session.add(ProjectMembership(project_id=p1.id, user_id=uid))
    for uid in [admin.id, manager.id, emp1.id]:
        db.session.add(ProjectMembership(project_id=p2.id, user_id=uid))
    db.session.flush()

    # ── Tasks for p1 ────────────────────────────────────────────────
    tasks_p1 = [
        Task(title='Design wireframes', description='Create wireframes for all main pages.', priority='high',
             status='done', deadline=today - timedelta(days=5), project_id=p1.id, assigned_to=emp1.id, created_by=manager.id),
        Task(title='Set up project repo', description='Initialize Git repo and CI/CD pipeline.', priority='medium',
             status='done', deadline=today - timedelta(days=3), project_id=p1.id, assigned_to=emp2.id, created_by=manager.id),
        Task(title='Build homepage', description='Implement responsive homepage from approved mockup.', priority='high',
             status='in_progress', deadline=today + timedelta(days=5), project_id=p1.id, assigned_to=emp1.id, created_by=manager.id),
        Task(title='Write API docs', description='Document all REST endpoints.', priority='low',
             status='todo', deadline=today + timedelta(days=14), project_id=p1.id, assigned_to=emp2.id, created_by=manager.id),
        Task(title='SEO audit', description='Run SEO analysis and fix issues.', priority='medium',
             status='todo', deadline=today + timedelta(days=20), project_id=p1.id, assigned_to=emp1.id, created_by=manager.id),
    ]

    # ── Tasks for p2 ────────────────────────────────────────────────
    tasks_p2 = [
        Task(title='Define user stories', description='Write user stories for MVP features.', priority='high',
             status='done', deadline=today - timedelta(days=10), project_id=p2.id, assigned_to=emp1.id, created_by=admin.id),
        Task(title='Design app screens', description='Create high-fidelity mockups for all screens.', priority='high',
             status='in_progress', deadline=today + timedelta(days=8), project_id=p2.id, assigned_to=emp1.id, created_by=admin.id),
        Task(title='Backend API setup', description='Set up Flask API with auth endpoints.', priority='high',
             status='todo', deadline=today + timedelta(days=15), project_id=p2.id, assigned_to=manager.id, created_by=admin.id),
    ]

    db.session.add_all(tasks_p1 + tasks_p2)
    db.session.flush()

    # ── Sample chat messages ─────────────────────────────────────────
    from datetime import datetime, timedelta as td
    msgs = [
        ChatMessage(body='Hey team, let\'s sync on the homepage design today.', project_id=p1.id, user_id=manager.id),
        ChatMessage(body='Wireframes are approved! Moving to development now.', project_id=p1.id, user_id=emp1.id),
        ChatMessage(body='I\'ll start on the API docs once the homepage is done.', project_id=p1.id, user_id=emp2.id),
        ChatMessage(body='Kickoff meeting notes shared in Notion.', project_id=p2.id, user_id=admin.id),
        ChatMessage(body='User stories document is ready for review.', project_id=p2.id, user_id=emp1.id),
    ]
    db.session.add_all(msgs)

    # ── Pending request ──────────────────────────────────────────────
    req = ProjectRequest(
        title='Customer Portal Dashboard',
        description='Build a self-service portal for customers to track orders and raise support tickets.',
        priority='high', deadline=today + timedelta(days=45), estimated_hours=80,
        requested_by=emp1.id, status='pending'
    )
    db.session.add(req)
    db.session.commit()


@login_manager.user_loader
def load_user(user_id):
    from models import User
    return db.session.get(User, int(user_id))


if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
