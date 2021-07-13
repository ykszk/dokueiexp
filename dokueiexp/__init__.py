import os
import json
from collections import namedtuple
import tempfile
from functools import wraps

import flask
from flask import render_template
import flask_login
from flask_login import login_required
import pandas as pd
from . import recorder

Slider = namedtuple('Slider',
                    ['label_id', 'label', 'label_left', 'label_right'])


class User(flask_login.UserMixin):
    def __init__(self, username):
        self.id = username
        self.username = username


def create_app(test_config=None):
    app = flask.Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'dokuei.sqlite3'),
        USERS_CSV=os.environ.get('USERS_CSV', 'users.csv'),
        CASE_IDS_TXT=os.environ.get('CASE_IDS_TXT', 'case_ids.txt'),
        ITEMS_CSV=os.environ.get('ITEMS_CSV', 'items.csv'),
        RECORD_DB=os.environ.get('RECORD_DB', 'sqlite:///records.sqlite3'))

    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    login_manager = flask_login.LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'

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
    sliders = df_items.apply(lambda row: Slider(row.get('id'), row.get('name'),
                                                row.left, row.right),
                             axis=1)

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

    def record_data2obj(data):
        return json.loads(data.decode('utf8'))

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
                users_progress[username] = dict(
                    progress=progress, completed=progress == len(case_ids))
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
        return user_dashboard(username, '{}のダッシュボード'.format(username))

    def user_dashboard(username, title='ダッシュボード'):
        with db.new_session() as sess:
            recs = sess.query(db.Record).filter_by(username=username)
            rec_dict = {r.case_id: r.completed for r in recs}
            n_done = sum([1 for r in rec_dict.values() if r])
        return render_template('index.html',
                               title=title,
                               username=username,
                               case_ids=case_ids,
                               progress='{}/{}'.format(n_done, len(case_ids)),
                               records=rec_dict)

    @app.route('/user/<username>/case/<case_id>')
    @login_required
    @admin_required
    def admin_user_case(username, case_id):
        if username not in users:
            flask.flash('User: {} not found.'.format(username), 'failed')
            return flask.redirect('/')
        return render_case(username, case_id, True)

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
        username = flask_login.current_user.username
        flask_login.logout_user()
        flask.flash(username + ' logged out.', 'success')
        return flask.redirect('/')

    def render_case(username, case_id, read_only=False):
        '''
        read_only for admin view
        '''
        if case_id in case_ids_set:
            with db.new_session() as sess:
                rec = db.get_record(username, case_id, sess)
            if rec:
                data = json.loads(rec.data.decode('utf8'))
                completed = rec.completed
            else:
                data = {}
                completed = False
            return render_template('case.html',
                                   title=case_id,
                                   username=username,
                                   case_id=case_id,
                                   completed=completed,
                                   sliders=sliders,
                                   data=data,
                                   read_only=read_only)
        else:
            flask.flash('Case "{}" not found.'.format(case_id), 'failed')
            return flask.redirect('/')

    @app.route('/case/<case_id>', methods=['GET', 'PUT'])
    @login_required
    def case(case_id):
        username = flask_login.current_user.id
        if username == 'admin':
            flask.flash('Invalid page for admin', 'failed')
            return flask.redirect('/')
        if flask.request.method == 'GET':
            return render_case(username, case_id)
        else:
            if case_id in case_ids:
                with db.new_session() as sess:
                    data = flask.request.get_data()
                    data_obj = record_data2obj(data)
                    db.update_record(username, case_id, data,
                                     len(data_obj) >= len(df_items), sess)
                    return {'result': 'success'}
            else:
                return {'result': 'failure', 'reason': 'case_id not found'}

    return app
