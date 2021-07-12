set FLASK_APP=dokueiexp
set FLASK_ENV=production
set USERS_CSV=tests/users.csv
set CASE_IDS_TXT=tests/case_ids.txt
set ITEMS_CSV=tests/items.csv
set RECORD_DB=sqlite:///tests/records.sqlite3
waitress-serve --call dokueiexp:create_app
