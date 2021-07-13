# Web system for 読影実験
[![codecov](https://codecov.io/gh/yk-szk/dokueiexp/branch/main/graph/badge.svg?token=JE8QNVF5NI)](https://codecov.io/gh/yk-szk/dokueiexp)

## Dev Run

### Windows
```bat
dokueiexp\run.bat
```

### Linux
```sh
bash dokueiexp/run.sh
```

Optionally add `--host 0.0.0.0` to allow other devices


## Deploy

```sh
pip install waitress .
waitress-serve --call dokueiexp:create_app
# or deploy.[bat,sh]
```
## Test
```sh
python -m pytest
```
