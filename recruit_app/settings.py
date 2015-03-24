# -*- coding: utf-8 -*-
import os
basedir = os.path.abspath(os.path.dirname(__file__))

os_env = os.environ

class Config(object):
    SECRET_KEY = os_env.get('RECRUIT_APP_SECRET', 'secret-key')  # TODO: Change me
    REDIS_URL = os.getenv('REDISTOGO_URL')
    APP_DIR = os.path.abspath(os.path.dirname(__file__))  # This directory
    PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))
    BCRYPT_LOG_ROUNDS = 13
    ASSETS_DEBUG = False
    DEBUG_TB_ENABLED = False  # Disable Debug toolbar
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    CACHE_TYPE = 'simple'  # Can be "memcached", "redis", etc.
    SECURITY_PASSWORD_HASH = 'bcrypt'
    SECURITY_LOGIN_USER_TEMPLATE = 'public/login.html'



class ProdConfig(Config):
    """Production configuration."""
    ENV = 'prod'
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os_env.get('DATABASE_URL')  # TODO: Change me
    DEBUG_TB_ENABLED = True  # Disable Debug toolbar
    WHOOSH_BASE = os.path.join(basedir, 'search.db')


class DevConfig(Config):
    """Development configuration."""
    ENV = 'dev'
    DEBUG = True
    DB_NAME = 'dev.db'
    # Put the db file in project root
    DB_PATH = os.path.join(Config.PROJECT_ROOT, DB_NAME)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///{0}'.format(DB_PATH)
    WHOOSH_BASE = os.path.join(basedir, 'search.db')
    DEBUG_TB_ENABLED = True
    ASSETS_DEBUG = True  # Don't bundle/minify static assets
    CACHE_TYPE = 'simple'  # Can be "memcached", "redis", etc.


class TestConfig(Config):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    BCRYPT_LOG_ROUNDS = 1  # For faster tests
    WTF_CSRF_ENABLED = False  # Allows form testing
