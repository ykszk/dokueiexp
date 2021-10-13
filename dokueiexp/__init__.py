import os
import json
from collections import namedtuple
import tempfile
from functools import wraps
from datetime import datetime, timedelta
import random

import flask
from flask import render_template
import flask_login
from flask_login import login_required
import pandas as pd
from . import recorder

Slider = namedtuple(
    'Slider',
    ['label_id', 'label', 'label_left', 'label_right', 'allow_center'])


class User(flask_login.UserMixin):
    def __init__(self, username):
        self.id = username


def admin_required(f):
    '''
    Use this decorator like below(the order matters.)
        @login_required
        @admin_required
    '''
    @wraps(f)
    def wrap(*args, **kwargs):
        if flask_login.current_user.id == "admin":
            return f(*args, **kwargs)
        else:
            flask.abort(403, 'Admin only page.')

    return wrap


def nonadmin_required(f):
    '''
    Use this decorator like below(the order matters.)
        @login_required
        @nonadmin_required
    '''
    @wraps(f)
    def wrap(*args, **kwargs):
        if flask_login.current_user.id != "admin":
            return f(*args, **kwargs)
        else:
            flask.abort(403, 'Invalid page for admin.')

    return wrap


def create_app(test_config=None):
    app = flask.Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        USERS_CSV=os.environ.get('USERS_CSV', 'users.csv'),
        CASE_IDS_TXT=os.environ.get('CASE_IDS_TXT', 'case_ids.txt'),
        ITEMS_CSV=os.environ.get('ITEMS_CSV', 'items.csv'),
        DIAGNOSIS_CSV=os.environ.get('DIAGNOSIS_CSV', 'diagnosis.csv'),
        REF_DATA_CSV=os.environ.get('REF_DATA_CSV', 'reference.csv'),
        INTERVAL=os.environ.get('INTERVAL', '1'),
        RECORD_DB=os.environ.get('RECORD_DB', 'sqlite:///records.sqlite3'))

    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    MIN_DELTA = timedelta(minutes=float(app.config['INTERVAL']))
    print('interval', MIN_DELTA)

    app.permanent = True
    permanent_session_lifetime = int(os.environ.get('SESSION_LIFETIME', '300'))
    app.permanent_session_lifetime = timedelta(
        minutes=permanent_session_lifetime)

    login_manager = flask_login.LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    rng_seeds = {}

    df_users = pd.read_csv(app.config['USERS_CSV'])
    users = {
        username: {
            'password': pw
        }
        for username, pw in zip(df_users['username'], df_users['password'])
    }
    print(len(users), 'users found.')
    with open(app.config['CASE_IDS_TXT']) as f:
        case_ids = f.read().splitlines()
    case_ids_set = set(case_ids)

    df_items = pd.read_csv(app.config['ITEMS_CSV'], encoding='cp932')
    print(len(df_items), 'items found.')
    df_diagnosis = pd.read_csv(app.config['DIAGNOSIS_CSV'], encoding='cp932')
    print(len(df_diagnosis), 'diagnosis items found.')
    slider_groups = {}
    for group, df_group in df_items.groupby('group', sort=False):
        slider_groups[group] = df_group.apply(
            lambda row: Slider(row.get('id'), row.get('name'), row.left, row.
                               right, row.allow_center),
            axis=1)

    df_ref = pd.read_csv(app.config['REF_DATA_CSV'],
                         index_col='id',
                         encoding='cp932')
    assert set(df_ref.index) == case_ids_set, 'Invalid input'
    assert set(df_ref.columns) == set(df_items['id'].values), 'Invalid input'

    ref_dict = {}
    for case_id in df_ref.index:
        ref_dict[case_id] = df_ref.loc[case_id].to_dict()

    db = recorder.RecordDB(app.config['RECORD_DB'], False)

    @login_manager.user_loader
    def user_loader(username):
        if username not in users:
            return

        user = User(username)
        return user

    @login_manager.request_loader
    def request_loader(request):
        username = request.form.get('username')
        if username not in users:
            return

        user = User(username)
        user.is_authenticated = request.form['password'] == users[username][
            'password']

        return user

    def obj2bytes(obj):
        return json.dumps(obj).encode('utf8')

    @app.errorhandler(403)
    def page_forbidden(e):
        return render_template('error.html', title='403 Forbidden.',
                               error=e), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('error.html',
                               title='404 Page not found',
                               error=e), 404

    @app.route('/admin')
    @login_required
    @admin_required
    def admin():
        users_progress = {}
        with db.new_session() as sess:
            for username in df_users['username']:
                if username == 'admin':
                    continue
                matches = sess.query(db.Record).filter_by(username=username,
                                                          completed=True)
                progress = matches.count()
                users_progress[username] = dict(progress=progress,
                                                completed=progress == 2 *
                                                len(case_ids))
        return render_template('admin.html',
                               title='Admin page',
                               users_progress=users_progress)

    @app.route('/admin/download/csv')
    @login_required
    @admin_required
    def csv():
        with tempfile.NamedTemporaryFile(suffix='.csv') as temp:
            temp.close()
            with db.new_session() as sess:
                db.to_csv(temp.name, sess)
            return flask.send_file(temp.name, as_attachment = True, \
        attachment_filename = 'database.csv', \
        mimetype = 'text/csv')

    @app.route('/user/<username>/')
    @login_required
    @admin_required
    def admin_user(username):
        if username not in users:
            flask.flash('User: {} not found.'.format(username), 'failed')
            return flask.redirect('/')
        return user_dashboard(username,
                              '{}のダッシュボード'.format(username),
                              admin=True)

    def user_dashboard(username, title='ダッシュボード', admin=False):
        with db.new_session() as sess:
            recs = sess.query(db.Record).filter_by(username=username, ai=False)
            rec_dict = {r.case_id: r for r in recs}
            n_done = sum([1 for r in rec_dict.values() if r.completed])
            ai_recs = sess.query(db.Record).filter_by(username=username,
                                                      ai=True)
            ai_rec_dict = {r.case_id: r for r in ai_recs}
            ai_n_done = sum([1 for r in ai_rec_dict.values() if r.completed])
        if admin:
            shuffled_case_ids = case_ids
        else:
            seed = rng_seeds.get(username, 0)
            random.seed(seed)
            shuffled_case_ids = random.sample(case_ids, len(case_ids))
        return render_template('index.html',
                               title=title,
                               username=username,
                               case_ids=shuffled_case_ids,
                               progress='{}/{}, {}/{}'.format(
                                   n_done, len(case_ids), ai_n_done,
                                   len(case_ids)),
                               records=rec_dict,
                               ai_records=ai_rec_dict,
                               now=datetime.now(),
                               min_delta=MIN_DELTA)

    @app.route('/user/<username>/<w_wo>/case/<case_id>')
    @login_required
    @admin_required
    def admin_user_case(username, case_id, w_wo):
        if username not in users:
            flask.flash('User: {} not found.'.format(username), 'failed')
            return flask.redirect('/')
        return render_case(username, case_id, w_wo == 'w', True)

    @app.route('/', methods=['GET'])
    def root():
        if flask_login.current_user.is_authenticated:
            if flask_login.current_user.id == 'admin':
                return flask.redirect('/admin')
            else:
                return user_dashboard(flask_login.current_user.id)
        else:
            return flask.redirect('/login')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if flask.request.method == 'GET':
            if flask_login.current_user.is_authenticated:
                return flask.redirect('/')
            else:
                return flask.render_template('login.html', title='ログイン')

        if flask.request.method == 'POST':
            username = flask.request.form['username']
            if username not in users:
                flask.flash('User "{}" not found.'.format(username), 'failed')
                return flask.redirect('/login')

            if flask.request.form['password'] == users[username]['password']:
                user = User(username)
                flask_login.login_user(user)
                rng_seeds[username] = random.randint(0, 10000)
                next_url = flask.request.args.get('next')
                if next_url:
                    return flask.redirect(next_url)
                else:
                    return flask.redirect('/')
            else:
                flask.flash('Invalid password for "{}".'.format(username),
                            'failed')
                return flask.redirect('/login')

        return 'Bad login'

    @app.route('/logout')
    @login_required
    def logout():
        username = flask_login.current_user.id
        flask_login.logout_user()
        flask.flash(username + ' logged out.', 'success')
        return flask.redirect('/')

    def render_case(username, case_id, ai, read_only=False):
        '''
        read_only for admin view
        '''
        if case_id in case_ids_set:
            if ai:  # to edit w/ ai, w/o ai needs to be completed and MIN_DELTA
                with db.new_session() as sess:
                    wo_rec = db.get_record(username, case_id, False, sess)
                if (not wo_rec) or (wo_rec and not wo_rec.completed) or (
                        wo_rec and
                    (datetime.now() - wo_rec.last_update < MIN_DELTA)):
                    flask.flash('{}はまだ読影できません。'.format(case_id), 'failed')
                    return flask.redirect('/')

            with db.new_session() as sess:
                rec = db.get_record(username, case_id, ai, sess)
            if rec:
                data = json.loads(rec.data.decode('utf8'))
                completed = rec.completed
                if completed:
                    flask.flash('{}はすでに確定しています。'.format(case_id), 'failed')
                    return flask.redirect('/')
                elapsed_time = rec.elapsed_time
            else:
                data = {}
                completed = False
                elapsed_time = 0
            if ai:
                ref_data = ref_dict[case_id]
            else:
                ref_data = {}
            return render_template('case.html',
                                   title=case_id,
                                   username=username,
                                   case_id=case_id,
                                   completed=completed,
                                   elapsed_time=elapsed_time,
                                   slider_groups=slider_groups,
                                   diagnosis_items=df_diagnosis,
                                   ref_data=ref_data,
                                   data=data,
                                   read_only=read_only)
        else:
            flask.flash('Case "{}" not found.'.format(case_id), 'failed')
            return flask.redirect('/')

    @app.route('/<w_wo>/case/<case_id>', methods=['GET', 'PUT'])
    @login_required
    @nonadmin_required
    def case(case_id, w_wo):
        is_ai = w_wo == 'w'
        username = flask_login.current_user.id
        if flask.request.method == 'GET':
            return render_case(username, case_id, is_ai)
        else:
            if case_id in case_ids:
                with db.new_session() as sess:
                    data = recorder.record_data2obj(flask.request.get_data())
                    et = data.pop('elapsed_time', 0)
                    data = obj2bytes(data)
                    db.update_record(username, case_id, data, et, is_ai, False,
                                     sess)
                    return {'result': 'success'}, 200
            else:
                return {
                    'result': 'failure',
                    'reason': 'case_id not found'
                }, 404

    @app.route('/<w_wo>/case/<case_id>/fix', methods=['PUT'])
    @login_required
    @nonadmin_required
    def fix_case(case_id, w_wo):
        is_ai = w_wo == 'w'
        username = flask_login.current_user.id
        if case_id in case_ids:
            with db.new_session() as sess:
                data = recorder.record_data2obj(flask.request.get_data())
                et = data.pop('elapsed_time', 0)
                data = obj2bytes(data)
                db.update_record(username, case_id, data, et, is_ai, True,
                                 sess)
                if not is_ai:  # copy to ai
                    db.update_record(username, case_id, data, 0, True, False,
                                     sess)
                return {'result': 'success'}, 200
        else:
            return {'result': 'failure', 'reason': 'case_id not found'}, 404

    return app
