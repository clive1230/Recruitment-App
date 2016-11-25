from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_security.decorators import login_required
from flask_security import current_user, roles_accepted

from recruit_app.user.models import EveCharacter
from recruit_app.recruit.models import HrApplication, HrApplicationComment
from recruit_app.recruit.managers import RecruitManager
from recruit_app.recruit.forms import HrApplicationForm, HrApplicationCommentForm, HrApplicationCommentEdit, SearchForm
from recruit_app.blacklist.models import BlacklistCharacter, BlacklistGSF

from sqlalchemy import desc, asc


blueprint = Blueprint("recruit", __name__, url_prefix='/recruits',
                        static_folder="../static")


@blueprint.route("/my_applications/", methods=['GET'])
@blueprint.route("/my_applications/<int:page>", methods=['GET'])
@login_required
def applications(page=1):
    query = HrApplication.query.filter(HrApplication.hidden == False, HrApplication.user_id == current_user.get_id()).order_by(desc(HrApplication.id))
    personal_applications = query.paginate(page, current_app.config['MAX_NUMBER_PER_PAGE'], False)

    return render_template('recruit/applications.html', personal_applications=personal_applications)


@blueprint.route("/application_queue/", methods=['GET', 'POST'])
@blueprint.route("/application_queue/<int:page>/<int:filter>", methods=['GET', 'POST'])
@login_required
@roles_accepted('admin', 'recruiter', 'reviewer')
def application_queue(page=1, filter=0):

    search_form = SearchForm()

    if request.method == 'POST' and search_form.validate_on_submit() and search_form.search.data:
        query = HrApplication.query.outerjoin(EveCharacter, EveCharacter.user_id == HrApplication.user_id).filter(
            EveCharacter.character_name.ilike("%" + str(search_form.search.data) + "%")|
            HrApplication.main_character_name.ilike(unicode("%" + search_form.search.data + "%")))

        query2 = HrApplication.query.filter(HrApplication.characters.any(EveCharacter.character_name.ilike("%" + str(search_form.search.data) + "%")))
        query = query.union(query2)

        page = 1 # Reset the page to 1 on search

    elif filter == 1: # All apps
        query = HrApplication.query.filter(HrApplication.hidden == False)
    elif filter == 0: # Current applications
        query = HrApplication.query.filter(
            HrApplication.hidden == False,
            HrApplication.approved_denied != "Closed",
            HrApplication.approved_denied != "Rejected",
            HrApplication.approved_denied != "Approved")
    else: # filter == 2, Current user's applications         
        query = HrApplication.query.filter(HrApplication.hidden == False)
        query2 = query.filter(
            (HrApplication.reviewer_user_id == current_user.get_id()) |
            (HrApplication.last_user_id == current_user.get_id()))
        query = query.join(HrApplicationComment, (HrApplication.id == HrApplicationComment.application_id) & (HrApplicationComment.user_id == current_user.get_id()))
        query = query.union(query2)

    if current_user.has_role('training'):
        query = query.order_by(HrApplication.training.desc(), HrApplication.id)
    else:
        query = query.order_by(HrApplication.id)
    
    # Add sort and pagination options to the query
    recruiter_queue = query.paginate(page, current_app.config['MAX_NUMBER_PER_PAGE'], False)

    return render_template('recruit/application_queue.html', recruiter_queue=recruiter_queue, search_form=search_form)


@blueprint.route("/applications/create", methods=['GET', 'POST'])
@login_required
def application_create():
    form = HrApplicationForm()

    characters = EveCharacter.query.filter_by(user_id=current_user.get_id()).all()
    character_choices = []
    for character in characters:
        character_choices = character_choices + [(character.character_id, character.character_name)]

    form.characters.choices = character_choices

    if request.method == 'POST':
        if form.validate_on_submit():
            application = RecruitManager.create_application(form, user=current_user)

            flash("Application created. We will contact you on your main character by EVE mail if we require additional information. You will receive an in-game notification when you are invited to join.", category='message')
            return redirect(url_for('recruit.application_view', application_id=application.id))

    return render_template('recruit/application_create.html',
                           form=form)


@blueprint.route("/applications/<int:application_id>/", methods=['GET', 'POST'])
@login_required
def application_view(application_id):
    comments = []
    characters = []
    related = []

    form_app = HrApplicationForm()
    form_comment = HrApplicationCommentForm()
    form_edit = HrApplicationCommentEdit()

    query = HrApplication.query.filter_by(id=application_id)
    application = query.first()
    if application:
        if current_user.has_role("recruiter") or current_user.has_role("admin") or current_user.has_role('reviewer'):
            characters = EveCharacter.query.filter_by(user_id=application.user_id).order_by(EveCharacter.api_id).all()
            characters += EveCharacter.query.filter(EveCharacter.previous_users.any(id=application.user_id)).all()

            evewho = {}
            for character in characters:
                evewho[character.character_name] = character.character_name.replace(' ','+')

            # Get related applications
            related = HrApplication.query.filter(HrApplication.user_id == application.user_id, HrApplication.id != application.id).order_by(HrApplication.id).all()

            comments = HrApplicationComment.query.filter_by(
                application_id=application_id)\
                .order_by(asc(HrApplicationComment.created_time))\
                .all()

            blacklist_clean = True

            # Check for IPs on the blacklist
            blacklist_ips = list(set([x.ip_address for x in BlacklistCharacter.query.all() if x.ip_address is not None and x.ip_address is not u'']))
            ips = [i for e in blacklist_ips for i in application.user.get_ips() if e in i]
            if len(ips) > 0:
                flash("Heads up this person's IP is on the blacklist:" + unicode(ips), 'error')
                blacklist_clean = False

            # Check for character names on the GSF RC Blacklist
            gsf_blacklist = {}
            for character in characters:
                gsf_blacklist[character.character_name] = "UNKNOWN"

            gsf_blacklist_str = ''
            for character in characters:
                result = BlacklistGSF.getStatus(character)
                gsf_blacklist[character.character_name] = result
                if result != 'NOT FOUND' and result != 'CLEARED':
                    gsf_blacklist_str += ' ' + character.character_name

            if len(gsf_blacklist_str) > 0:
                flash("Check GSF blacklist results for character(s)" + unicode(gsf_blacklist_str), 'error')
                blacklist_clean = False

            # Check for character names on the internal blacklist
            blacklist_string = ''
            for character in characters:
                blacklist_string = blacklist_string + ' ' + str(character.character_name)

            # blacklist_query = BlacklistCharacter.query.whoosh_search(blacklist_string, or_=True).all()
            query = BlacklistCharacter.query.filter(BlacklistCharacter.name.in_([x.character_name for x in characters])).all()

            if query:
                flash('Double check blacklist, ' + str(query) + ' matched', 'error')
                blacklist_clean = False

            if blacklist_clean:
                flash('All blacklists are clean.')

            return render_template('recruit/application.html',
                                   application=application,
                                   characters=characters,
                                   related=related,
                                   comments=comments,
                                   form_comment=form_comment,
                                   form_edit=form_edit,
                                   form_app=form_app,
                                   gsf_blacklist=gsf_blacklist,
                                   evewho=evewho)

        elif int(application.user_id) == int(current_user.get_id()):

            return render_template('recruit/application.html',
                                   application=application,
                                   form_app=form_app)

    return redirect(url_for('recruit.applications'))


@blueprint.route("/applications/<application_id>/comment/", methods=['POST'])
@login_required
@roles_accepted('admin', 'recruiter', 'reviewer')
def application_comment_create(application_id):
    form_comment = HrApplicationCommentForm()

    application = HrApplication.query.filter_by(id=int(application_id)).first()

    if application:
        if request.method == 'POST':
            if form_comment.validate_on_submit():
                RecruitManager.create_comment(application, form_comment.comment.data, current_user)

        return redirect(url_for('recruit.application_view', application_id=application_id))

    return redirect(url_for('recruit.applications'))

@blueprint.route("/applications/<int:application_id>/comment/<int:comment_id>/<action>/", methods=['GET', 'POST'])
@login_required
def application_comment_action(application_id, comment_id, action):
    form_edit = HrApplicationCommentForm()

    if current_user.has_role("recruiter") or current_user.has_role("admin") or current_user.has_role('reviewer'):
        if HrApplication.query.filter_by(id=int(application_id)).first():
            if HrApplicationComment.query.filter_by(id=comment_id).first():

                comment = HrApplicationComment.query.filter_by(id=comment_id).first()

                if comment.user_id == int(current_user.get_id()) or current_user.has_role("admin"):
                    if request.method == 'POST':
                        if action == "edit":
                            if form_edit.validate_on_submit():
                                RecruitManager.edit_comment(comment, form_edit.comment.data, current_user.get_id())

                        elif action == "delete":
                            comment.delete()

                    elif action == "delete":
                        comment.delete()
            return redirect(url_for('recruit.application_view', application_id=application_id))

    return redirect(url_for('recruit.applications'))


@blueprint.route("/applications/<int:application_id>/<action>", methods=['GET', 'POST'])
@login_required
def application_interact(application_id, action):
    application_status = None

    if current_user.main_character_id == None:
        return redirect(url_for('user.eve_characters'))

    application = HrApplication.query.filter_by(id=application_id).first()
    if application:
        if current_user.has_role('admin') or current_user.has_role('recruiter') or current_user.has_role('reviewer'):
            if current_user.has_role("admin") or (action not in ['delete', 'hide', 'unhide']):
                if current_user.has_role('recruiter') or current_user.has_role('admin') or (action not in ['approve', 'reject', 'close', 'training']):
                    application_status = RecruitManager.alter_application(application, action, current_user)

                    flash("%s's application %s" % (application.main_character_name,
                                                   application_status),
                          category='message')

        elif application.user_id == current_user.get_id():
            if action == "delete" and application.approve_deny == "New":
                application_status = RecruitManager.alter_application(application, action, current_user)
                flash("%s's application %s" % (application.main_character,
                                               application_status),
                      category='message')

        if action == 'training' or action == 'hide':
            return redirect(request.referrer)

        elif application_status and application_status != "deleted":
            return redirect(url_for('recruit.application_view', application_id=application.id))

    return redirect(url_for('recruit.applications'))
