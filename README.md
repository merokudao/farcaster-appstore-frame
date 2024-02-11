Set env variables by `set -a; source .env; set +a`


RUN using `flask run --host 0.0.0.0 --port 9091`


## Docker

### Build

`docker build -t roastme .`

### Run

`docker run -p 9091:5000 --env-file .env roastme`

## Check

`ruff .`