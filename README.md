# Web system for 読影実験

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
```
## Test
```sh
python -m pytest
```
