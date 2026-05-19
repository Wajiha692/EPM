from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='employee')
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    memberships = db.relationship('ProjectMembership', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    requests = db.relationship('ProjectRequest', backref='requester', lazy='dynamic', foreign_keys='ProjectRequest.requested_by')
    assigned_tasks = db.relationship('Task', foreign_keys='Task.assigned_to', backref='assignee', lazy='dynamic')
    created_tasks = db.relationship('Task', foreign_keys='Task.created_by', backref='creator', lazy='dynamic')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')
    messages = db.relationship('ChatMessage', backref='sender', lazy='dynamic')

    def set_password(self, p): self.password_hash = generate_password_hash(p)
    def check_password(self, p): return check_password_hash(self.password_hash, p)
    def is_admin(self): return self.role == 'admin'
    def is_manager(self): return self.role in ('admin', 'manager')

    @property
    def avatar_initials(self):
        parts = self.full_name.split()
        return (parts[0][0] + parts[-1][0]).upper() if len(parts) >= 2 else self.full_name[:2].upper()

    def is_member_of(self, project_id):
        return self.memberships.filter_by(project_id=project_id).first() is not None

    def projects_list(self):
        if self.is_manager():
            return Project.query.order_by(Project.created_at.desc()).all()
        return [m.project for m in self.memberships.join(Project).order_by(Project.created_at.desc())]


class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(30), nullable=False, default='active')
    priority = db.Column(db.String(20), default='medium')
    deadline = db.Column(db.Date)
    estimated_hours = db.Column(db.Integer)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    memberships = db.relationship('ProjectMembership', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    tasks = db.relationship('Task', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    messages = db.relationship('ChatMessage', backref='project', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def total_tasks(self): return self.tasks.count()

    @property
    def done_tasks(self): return self.tasks.filter_by(status='done').count()

    @property
    def progress(self):
        t = self.total_tasks
        return round(self.done_tasks / t * 100) if t else 0

    @property
    def member_count(self): return self.memberships.count()

    @property
    def overdue_count(self):
        from datetime import date
        return self.tasks.filter(Task.deadline < date.today(), Task.status != 'done').count()

    def get_members(self):
        return [m.user for m in self.memberships.all()]


class ProjectMembership(db.Model):
    __tablename__ = 'project_memberships'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role_in_project = db.Column(db.String(20), default='member')
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('project_id', 'user_id'),)


class ProjectRequest(db.Model):
    __tablename__ = 'project_requests'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    priority = db.Column(db.String(20), default='medium')
    deadline = db.Column(db.Date)
    estimated_hours = db.Column(db.Integer)
    status = db.Column(db.String(20), default='pending')
    requested_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    rejection_reason = db.Column(db.Text)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    reviewer = db.relationship('User', foreign_keys=[reviewed_by])
    approved_project = db.relationship('Project', foreign_keys=[project_id])


class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    priority = db.Column(db.String(20), default='medium')
    status = db.Column(db.String(30), default='todo')
    deadline = db.Column(db.Date)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    comments = db.relationship('Comment', backref='task', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def is_overdue(self):
        from datetime import date
        return bool(self.deadline and self.status != 'done' and self.deadline < date.today())


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
