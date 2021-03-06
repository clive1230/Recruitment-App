# -*- coding: utf-8 -*-
import datetime as dt

from flask_security import UserMixin, RoleMixin
from flask_security.utils import verify_and_update_password, encrypt_password
from recruit_app.extensions import bcrypt
from recruit_app.database import Column, db, Model, ReferenceCol, relationship, SurrogatePK, TimeMixin

roles_users = db.Table('roles_users',
        db.Column('user_id', db.Integer(), db.ForeignKey('users.id')),
        db.Column('role_id', db.Integer(), db.ForeignKey('roles.id')))


class Role(SurrogatePK, Model, RoleMixin):
    __tablename__ = 'roles'
    name = Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

    def __repr__(self):
        return '<Role({name})>'.format(name=self.name)


class User(SurrogatePK, Model, UserMixin):
    __tablename__ = 'users'

    email = Column(db.String(80), unique=True, nullable=False)
    #: The hashed password
    password = Column(db.String(128), nullable=True)
    created_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    active = Column(db.Boolean(), default=False)
    is_admin = Column(db.Boolean(), default=False)

    confirmed_at = Column(db.DateTime, nullable=True)

    last_login_at = Column(db.DateTime())
    current_login_at = Column(db.DateTime())
    last_login_ip = Column(db.String(100))
    current_login_ip = Column(db.String(100))
    login_count = Column(db.Integer)

    roles = db.relationship('Role', secondary=roles_users, backref=db.backref('users', lazy='dynamic'), lazy='dynamic')

    main_character_id = ReferenceCol('characters', pk_name='character_id', nullable=True)
    main_character = relationship('EveCharacter', backref='user_main_character', foreign_keys=[main_character_id])

    def set_password(self, password):
        self.password = encrypt_password(password)
        self.save()

    def check_password(self, value):
        return verify_and_update_password(value, self)

    @classmethod
    def create(self, **kwargs):
        """Create a new record and save it the database."""
        instance = self(**kwargs)
        if kwargs['password']:
            instance.password = encrypt_password(kwargs['password'])
        return instance.save()

    @property
    def get_ips(self):
        return self.last_login_ip.split(', ') + self.current_login_ip.split(', ')

    def __repr__(self):
        return '<User({name})>'.format(name=self.email)

    def __str__(self):
        return self.email

previous_chars = db.Table('previous_chars',
    db.Column('user_id', db.Integer(), db.ForeignKey('users.id')),
    db.Column('character_id', db.String(254), db.ForeignKey('characters.character_id')))

class EveCharacter(Model, TimeMixin):
    __tablename__ = 'characters'

    character_id = Column(db.String(254), primary_key=True)
    character_name = Column(db.String(254))
    corporation_id = ReferenceCol('corporations', pk_name='corporation_id', nullable=True)
    corporation = relationship('EveCorporationInfo', backref='characters', foreign_keys=[corporation_id])

    api_id = ReferenceCol('api_key_pairs', pk_name='api_id', nullable=True)
    api = relationship('EveApiKeyPair', backref='characters', foreign_keys=[api_id])

    user_id = ReferenceCol('users', nullable=True)
    user = relationship('User', backref='characters', foreign_keys=[user_id])

    skillpoints = Column(db.Integer, nullable=True)
    previous_users = db.relationship('User', secondary=previous_chars, backref=db.backref('previous_chars', lazy='dynamic'), lazy='dynamic')

    def __str__(self):
        return self.character_name


class EveApiKeyPair(Model):
    __tablename__ = 'api_key_pairs'

    api_id = Column(db.String(254), primary_key=True)
    api_key = Column(db.String(254))
    last_update_time = Column(db.DateTime(), nullable=True)
    last_scraped_time = Column(db.DateTime(), nullable=True, default=dt.date(day=1, month=1, year=1980))

    user_id = ReferenceCol('users', nullable=True)
    user = relationship('User', backref='api_keys', foreign_keys=[user_id])

    valid = Column(db.Boolean, default=True)

    def __str__(self):
        return self.api_id

class EveAllianceInfo(Model):
    __tablename__ = 'alliances'

    alliance_id = Column(db.String(254), primary_key=True)
    alliance_name = Column(db.String(254))
    alliance_ticker = Column(db.String(254))
    executor_corp_id = Column(db.String(254))
    is_blue = Column(db.Boolean, default=False)
    member_count = Column(db.Integer)

    def __str__(self):
        return self.alliance_name


class EveCorporationInfo(Model):
    __tablename__ = 'corporations'

    corporation_id = Column(db.String(254), primary_key=True)
    corporation_name = Column(db.String(254))
    corporation_ticker = Column(db.String(254))
    member_count = Column(db.Integer)
    is_blue = Column(db.Boolean, default=False)
    alliance_id = ReferenceCol('alliances', pk_name='alliance_id', nullable=True)
    alliance = relationship('EveAllianceInfo', backref='corporations', foreign_keys=[alliance_id])

    def __str__(self):
        return self.corporation_name
