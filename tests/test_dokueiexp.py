import os
import tempfile
import json

import pytest
import pandas as pd
import dokueiexp

ITEMS_CSV = 'tests/items.csv'


@pytest.fixture
def client():
    db_fd, db_filename = tempfile.mkstemp(suffix='.sqlite3')
    config = dict(USERS_CSV='tests/users.csv',
                  CASE_IDS_TXT='tests/case_ids.txt',
                  ITEMS_CSV=ITEMS_CSV,
                  RECORD_DB='sqlite:///{}'.format(db_filename))
    app = dokueiexp.create_app(config)

    with app.test_client() as client:
        yield client

    os.close(db_fd)
    os.unlink(db_filename)


def login(client, username, password):
    return client.post('/login',
                       data=dict(username=username, password=password),
                       follow_redirects=True)


def logout(client):
    return client.get('/logout', follow_redirects=True)


def test_login_logout(client):
    """Make sure login and logout works."""

    rv = login(client, 'alice', 'alice')
    assert b'alice' in rv.data

    rv = logout(client)
    assert b'logged out' in rv.data

    rv = login(client, 'noone', 'noone')
    assert b'not found' in rv.data

    rv = login(client, 'alice', 'bob')
    assert b'Invalid password' in rv.data


def test_user(client):
    rv = login(client, 'alice', 'alice')
    assert b'alice' in rv.data

    rv = client.get('/case/Case001', follow_redirects=True)
    assert b'Case001' in rv.data
    assert b'Item01' in rv.data
    assert b'class="notset"' in rv.data

    df_items = pd.read_csv(ITEMS_CSV, encoding='cp932')
    item_ids = df_items['id'].to_list()
    # check recording
    # check progress
    rv = client.get('/', follow_redirects=True)
    assert b'0/10' in rv.data
    assert '✓'.encode('utf8') not in rv.data

    # set one
    rv = client.put('/case/Case001',
                    data=json.dumps({
                        item_ids[0]: '42'
                    }).encode('utf8'),
                    follow_redirects=True)
    assert b'success' in rv.data
    rv = client.get('/case/Case001', follow_redirects=True)
    assert b'42' in rv.data
    assert b'class="completed"' not in rv.data
    rv = client.put('/case/Case999',
                    data=json.dumps({
                        item_ids[0]: '42'
                    }).encode('utf8'),
                    follow_redirects=True)
    assert b'case_id not found' in rv.data

    # set all
    rv = client.put('/case/Case001',
                    data=json.dumps({iid: '50'
                                     for iid in item_ids}).encode('utf8'),
                    follow_redirects=True)
    assert b'success' in rv.data
    rv = client.get('/case/Case001', follow_redirects=True)
    assert b'class="completed"' in rv.data
    assert b'class="notset"' not in rv.data

    # check progress
    rv = client.get('/', follow_redirects=True)
    assert b'1/10' in rv.data
    assert '✓'.encode('utf8') in rv.data

    rv = logout(client)

    # check protection
    assert b'logged out' in rv.data
    rv = client.put('/case/Case001',
                    data=json.dumps({
                        item_ids[0]: '42'
                    }).encode('utf8'),
                    follow_redirects=True)
    assert b'Please log in' in rv.data


def test_admin(client):
    rv = login(client, 'admin', 'admin')
    assert b'admin' in rv.data
    assert b'alice' in rv.data
    assert b'bob' in rv.data

    rv = client.get('/case/Case001', follow_redirects=True)
    assert b'Invalid page for admin' in rv.data

    rv = client.get('/user/alice/', follow_redirects=True)
    assert b'alice' in rv.data
    assert b'Case001' in rv.data
    assert b'Case010' in rv.data

    rv = client.get('/user/alice/case/Case001', follow_redirects=True)
    assert b'alice' in rv.data
    assert b'Case001' in rv.data
    assert b'Case010' not in rv.data

    rv = logout(client)
    assert b'logged out' in rv.data

    # check protection
    rv = client.get('/admin', follow_redirects=True)
    assert b'Please log in to access this page' in rv.data
    assert 200 == rv.status_code
    rv = login(client, 'alice', 'alice')
    assert b'alice' in rv.data
    rv = client.get('/admin', follow_redirects=True)
    assert b'Admin only' in rv.data
    assert 403 == rv.status_code
    rv = client.get('/user/alice/', follow_redirects=True)
    assert b'Admin only' in rv.data
    assert 403 == rv.status_code
    rv = client.get('/user/alice/case/Case001', follow_redirects=True)
    assert b'Admin only' in rv.data
    assert 403 == rv.status_code
