# Web system for 読影実験
[![codecov](https://codecov.io/gh/yk-szk/dokueiexp/branch/main/graph/badge.svg?token=JE8QNVF5NI)](https://codecov.io/gh/yk-szk/dokueiexp)

## Deploy

```sh
pip install -r requirements.txt
pip install waitress
waitress-serve --call dokueiexp:create_app
# or dokueiexp/deploy.[bat,sh]
```

## Config

### Env vars
- INTERVAL: The interval between exps (in minutes)
- USERS_CSV : filename
- CASE_IDS_TXT : filename
- ITEMS_CSV : filename
- REF_DATA_CSV : filename
- RECORD_DB : filename. e.g `sqlite:///records.sqlite3`

### Files
- USERS_CSV: csv file with username and password columns. Note that `admin` user is required.
- CASE_IDS_TXT: text file with case IDs.
- ITEMS_CSV: csv with the following columns.
  - id: id
  - name: display name
  - left: label for the slider's left
  - right: label for the slider's right
  - group: group display name
  - allow_center: allow central value in the slider (boolean)
- REF_DATA_CSV: csv with reference (AI) values. id(case IDs) + [item's IDs]

## Developement

### Windows
```bat
dokueiexp\run.bat
```

### Linux
```sh
bash dokueiexp/run.sh
```

Optionally add `--host 0.0.0.0` to allow access from other devices


## Test
```sh
python -m pytest
```
