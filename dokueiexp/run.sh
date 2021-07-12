export FLASK_APP=dokueiexp
export FLASK_ENV=development
export USERS_CSV=tests/users.csv
export CASE_IDS_TXT=tests/case_ids.txt
export ITEMS_CSV=tests/items.csv
flask run "$@"
