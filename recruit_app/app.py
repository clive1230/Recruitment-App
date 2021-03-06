# -*- coding: utf-8 -*-
'''The app module, containing the app factory function.'''
from flask import Flask, render_template
from flask_admin import Admin

from recruit_app.settings import ProdConfig
from recruit_app.assets import assets
from recruit_app.extensions import (
    bcrypt,
    cache_extension,
    db,
    # login_manager,
    security,
    user_datastore,
    migrate,
    sentry,
    debug_toolbar,
    bootstrap,
    # rqDashboard,
    # admin,
    mail,
    rq,
    misaka,
)
from recruit_app import public, user, recruit, blacklist, jkproxy, hr, ia

from recruit_app.public.forms import ConfirmRegisterFormRecaptcha


def create_app(config_object=ProdConfig):
    '''An application factory, as explained here:
        http://flask.pocoo.org/docs/patterns/appfactories/

    :param config_object: The configuration object to use.
    '''
    app = Flask(__name__)
    app.config.from_object(config_object)
    register_extensions(app)
    register_blueprints(app)
    register_errorhandlers(app)
    admin = Admin()
    register_admin(admin, db)
    # register_search(app)
    admin.init_app(app)
    # admin needs to be initialized oddly for tests to work.
    register_tasks()

    return app


def register_extensions(app):
    assets.init_app(app)
    bcrypt.init_app(app)
    cache_extension.init_app(app)
    db.init_app(app)
    # login_manager.init_app(app)
    security.init_app(app, user_datastore, register_blueprint=True,
                      confirm_register_form=ConfirmRegisterFormRecaptcha)
    debug_toolbar.init_app(app)
    bootstrap.init_app(app)
    # rqDashboard.init_app(app)
    sentry.init_app(app, logging=True)
    # admin.init_app(app)
    mail.init_app(app)
    rq.init_app(app)
    migrate.init_app(app, db)
    misaka.init_app(app)

    return None


def register_blueprints(app):
    app.register_blueprint(public.views.blueprint)
    app.register_blueprint(user.views.blueprint)
    app.register_blueprint(recruit.views.blueprint)
    app.register_blueprint(blacklist.views.blueprint)
    app.register_blueprint(jkproxy.blueprint)
    app.register_blueprint(hr.views.blueprint)
    app.register_blueprint(ia.views.blueprint)

    return None


def register_admin(admin, db):
    user.admin.register_admin_views(admin, db)
    blacklist.admin.register_admin_views(admin, db)
    recruit.admin.register_admin_views(admin, db)

    return None


def register_tasks():
    # schedule_tasks()

    return None


def register_search(app):
    recruit.search.register_search_models(app)
    blacklist.search.register_search_models(app)

    return None


def register_errorhandlers(app):
    def render_error(error):
        # If a HTTPException, pull the `code` attribute; default to 500
        error_code = getattr(error, 'code', 500)
        return render_template("{0}.html".format(error_code)), error_code
    for errcode in [401, 404, 500]:
        app.errorhandler(errcode)(render_error)
    return None
