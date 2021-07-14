# Web system for 読影実験
[![codecov](https://codecov.io/gh/yk-szk/dokueiexp/branch/main/graph/badge.svg?token=JE8QNVF5NI)](https://codecov.io/gh/yk-szk/dokueiexp)

## Deploy

```sh
pip install -r requirements.txt
pip install waitress
waitress-serve --call dokueiexp:create_app
# or dokueiexp/deploy.[bat,sh]
```

### Variables
- INTERVAL: The interval between exps (in minutes)


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
