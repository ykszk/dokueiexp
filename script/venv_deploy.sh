export FLASK_APP=dokueiexp
export FLASK_ENV=production
export USERS_CSV=tests/users.csv
export CASE_IDS_TXT=tests/case_ids.txt
export ITEMS_CSV=tests/items.csv
export DIAGNOSIS_CSV=tests/diagnosis.csv
export SESSION_LIFETIME=300
export REF_DATA_CSV=tests/reference.csv
export INTERVAL=129600
export RECORD_DB=sqlite:///tests/records.sqlite3
/home/suzuki/dokueiexp/.venv/bin/waitress-serve --port 80 --call dokueiexp:create_app
