import os
import tempfile
import json
import time

import pytest
import pandas as pd
import dokueiexp

ITEMS_CSV = 'tests/items.csv'
INTERVAL_SEC = 2


@pytest.fixture
def client():
    with tempfile.NamedTemporaryFile() as temp:
        temp.close()
        db_filename = temp.name
        config = dict(USERS_CSV='tests/users.csv',
                      CASE_IDS_TXT='tests/case_ids.txt',
                      ITEMS_CSV=ITEMS_CSV,
                      DIAGNOSIS_CSV='tests/diagnosis.csv',
                      REF_DATA_CSV='tests/reference.csv',
                      INTERVAL=str(INTERVAL_SEC / 60),
                      RECORD_DB='sqlite:///{}'.format(db_filename))
        app = dokueiexp.create_app(config)

        with app.test_client() as client:
            yield client


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

    rv = client.get('/wo/case/Case001', follow_redirects=True)
    assert b'Case001' in rv.data
    assert b'Item01' in rv.data
    assert b'class="notset"' in rv.data

    df_items = pd.read_csv(ITEMS_CSV, encoding='cp932')
    item_ids = df_items['id'].to_list()

    # check progress
    rv = client.get('/', follow_redirects=True)
    assert b'0/4' in rv.data
    assert '未'.encode('utf8') in rv.data
    assert '<td>完了</td>'.encode('utf8') not in rv.data

    # set one
    rv = client.put('/wo/case/Case001',
                    data=json.dumps({
                        item_ids[0]: '42'
                    }).encode('utf8'),
                    follow_redirects=True)
    assert b'success' in rv.data
    assert 200 == rv.status_code
    rv = client.get('/wo/case/Case001', follow_redirects=True)
    assert b'42' in rv.data
    assert b'class="completed"' not in rv.data
    assert 200 == rv.status_code
    rv = client.put('/wo/case/Case999',
                    data=json.dumps({
                        item_ids[0]: '42'
                    }).encode('utf8'),
                    follow_redirects=True)
    assert b'case_id not found' in rv.data
    assert 404 == rv.status_code

    # set all
    rv = client.put('/wo/case/Case001',
                    data=json.dumps({iid: '50'
                                     for iid in item_ids}).encode('utf8'),
                    follow_redirects=True)
    assert 200 == rv.status_code
    assert b'success' in rv.data

    rv = client.get('/wo/case/Case001', follow_redirects=True)
    assert b'class="notset"' not in rv.data
    assert '一時保存'.encode('utf8') in rv.data

    rv = client.get('/w/case/Case001', follow_redirects=True)
    assert 'はまだ読影できません。'.encode('utf8') in rv.data

    # fix
    rv = client.put('/wo/case/Case001/fix',
                    data=json.dumps({iid: '50'
                                     for iid in item_ids}).encode('utf8'),
                    follow_redirects=True)
    assert 200 == rv.status_code
    assert b'success' in rv.data

    # test the interval
    rv = client.get('/', follow_redirects=True)
    assert '待'.encode('utf8') in rv.data

    rv = client.get('/w/case/Case001', follow_redirects=True)
    assert 'はまだ読影できません。'.encode('utf8') in rv.data

    time.sleep(INTERVAL_SEC)
    rv = client.get('/w/case/Case001', follow_redirects=True)
    assert b'class="notset"' not in rv.data
    assert '一時保存'.encode('utf8') in rv.data

    # test progress
    rv = client.get('/', follow_redirects=True)
    assert b'1/4, 0/4' in rv.data
    assert '未'.encode('utf8') in rv.data
    assert '<td>完了</td>'.encode('utf8') in rv.data

    rv = client.get('/wo/case/Case001', follow_redirects=True)
    assert 'すでに確定しています。'.encode('utf8') in rv.data

    rv = logout(client)

    # check protection
    assert b'logged out' in rv.data
    rv = client.put('/wo/case/Case001',
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

    rv = client.get('/wo/case/Case001', follow_redirects=True)
    assert b'Invalid page for admin' in rv.data

    for url in [
            '/wo/case/Case001', '/w/case/Case001', '/wo/case/Case001/fix',
            '/w/case/Case001/fix'
    ]:
        rv = client.put(url, follow_redirects=True)
        assert b'Invalid page for admin' in rv.data
        assert 403 == rv.status_code

    rv = client.get('/user/alice/', follow_redirects=True)
    assert b'alice' in rv.data
    assert b'Case001' in rv.data
    assert b'Case004' in rv.data

    rv = client.get('/user/alice/wo/case/Case001', follow_redirects=True)
    assert b'alice' in rv.data
    assert b'Case001' in rv.data
    assert b'Case004' not in rv.data

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
    rv = client.get('/user/alice/wo/case/Case001', follow_redirects=True)
    assert b'Admin only' in rv.data
    assert 403 == rv.status_code
