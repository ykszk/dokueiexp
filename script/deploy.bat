set FLASK_APP=dokueiexp
set FLASK_ENV=production
set USERS_CSV=tests/users.csv
set CASE_IDS_TXT=tests/case_ids.txt
set ITEMS_CSV=tests/items.csv
set REF_DATA_CSV=tests/reference.csv
set INTERVAL=30240
set SESSION_LIFETIME=300
set RECORD_DB=sqlite:///tests/records.sqlite3
waitress-serve --call dokueiexp:create_app
