export FLASK_APP=dokueiexp
export FLASK_ENV=production
export USERS_CSV=tests/users.csv
export CASE_IDS_TXT=tests/case_ids.txt
export ITEMS_CSV=tests/items.csv
export RECORD_DB=sqlite:///tests/records.sqlite3
waitress-serve --call dokueiexp:create_app
