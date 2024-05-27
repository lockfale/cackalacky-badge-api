# Cackalackycon - Badge API

### Env
We transitioned to doppler to handle secrets, but the first iteration was used with a .env file.

### Environment Variables
| Env Name               | Description                    | Example              |
|------------------------|--------------------------------|----------------------|
| APP_NAME               | name of the app                | badge-api            |
| APP_ENV                | the application environment    | dev, test, prod, etc |
| AWS_LOGGER_ACCESS_KEY  | s3 IAM access key              | ...                  |
| AWS_LOGGER_SECRET_KEY  | s3 IAM access secret           | ...                  |
| OTEL_COLLECTOR_SVC     | metrics collector service name | otel-container       |
| PG_DB_HOST             | postgres host name             | localhost            |
| PG_DB_USER             | db user                        | ckc_user             |
| PG_DB_PASSWORD         | db user password               | somethingClever      |
| PG_DB_PORT             | port for the postgres db       | 5432                 |
| PG_DB_DATABASE         | postgres database              | cackalacky           |
| PG_DB_CONNECTION_LIMIT | connection limit               | 10                   |
| REDIS_HOST             | redis service name             | redis-container      |
| SKIP_METRICS           | Boolean to send to otel or not | False                |


## Non Docker

### Create virtualenv first
```bash
pip install virtualenv
virtualenv -p python3 ckcbadgeapi
. .\ckcbadgeapi\Scripts\activate
```

### Install requirements
```bash
pip install -r requirements.txt
```



### Run the API

#### With Doppler
```
doppler secrets set SKIP_METRICS=False
doppler run -- uvicorn api:app --host 0.0.0.0 --port 5000 --log-config log.ini
```

#### Without Doppler
You'll have to set variables prior to running. So either set them inline, or export.
```
SKIP_METRICS=True uvicorn api:app --host 0.0.0.0 --port 5000 --log-config log.ini
```

## Docker

### Build the image
``docker build -t cackalackyapi:dev .``

### Start the container

``docker run --name cackalackyapi -d -p 3001:5000 cackalackyapi:latest  -e DOPPLER_TOKEN="<token>" --network local-ckc``

### Stop the container
``docker stop cackalackyapi``

### Remove the container
``docker rm cackalackyapi``

### Access the container
``docker exec -it cackalackyapi /bin/bash``


# Network (docker)

To communicate with local redis & otel collector, create a docker network:
``docker network create local-ckc``

Then, run the containers with your network:
``docker run .. --network local-ckc``

# Redis

We use redis as a cache layer for badge registration and also as a message queue for the discord bot and score processor. 

For each badge that registers:
- Create a 8 character hash
- Store 2 kv pairs:
  - key: 8 char hash w/uuid & mac address
  - key: uuid&mac w/8 char hash 

We store both combinations for badge registration in case the user of the badge
exits the sign-up page. This enables the user to go back to the registration page on the
badge and keep the same hash while the TTL is still valid

```shell
docker run --name redis-container --volume=/data --workdir=/data -p 6379:6379 --network local-ckc -d redis:latest

docker run --network=local-ckc --workdir=/app -p 3002:5000
```

# Victoria Metrics

Using Victoria Metrics as a substitute for prometheus to see if we can't save some resources.
This isn't necessary for development or in this repo.
```Bash
docker pull victoriametrics/victoria-metrics:latest
docker run -it --rm -v $(pwd)/victoria-metrics-data:/victoria-metrics-data -p 8428:8428 --name victoriametrics victoriametrics/victoria-metrics:latest
```

# Open Telemetry

Fast API doesn't have auto instrumentation. So we can't use that, we'll be programmatically creating metrics.

Metrics middleware creates a few basic metrics.

```shell
# nothing has changed in the way that we run the app
doppler run -- uvicorn api:app --host 0.0.0.0 --port 5000 --log-config log.ini
```

If you run into issues with anything otel related, you may have to run (which is in the Dockerfile):
```shell
opentelemetry-bootstrap -a install
```

Potentially helpful:
https://stackoverflow.com/questions/63970177/how-to-set-an-opentelemetry-span-attribute-for-a-fastapi-route
https://jairoandres.com/fastapi-open-telemetry-elastic-cloud/

## Collector

We export our metrics to the otel collector, then victoria metrics reads from them

```shell
docker run otel/opentelemetry-collector --name otel-collector -p 4317:4317 -p 4318:4318 --network local --rm -v $(pwd)/open-telemetry/collector-config.yaml:/etc/otelcol/config.yaml 
docker run otel/opentelemetry-collector --name otel-collector -p 4317:4317 -p 4318:4318 --network local --rm -v ${pwd}\\open-telemetry\\collector-config.yaml:/etc/otelcol/config.yaml 
```

### Config

```yaml
# local - REMEMBER TO RUN ALL LOCAL CONTAINERS with --network local-ckc
# <name of victoria container> -> is local only, in k8s we'll use the service
# to quiet some of the logs, remove "debug" from the exporter
exporters:
    debug:
      verbosity: detailed
    prometheusremotewrite:
      endpoint: http://<name of victoria container>:8428/api/v1/write
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318
service:
  pipelines:
    traces:
      receivers: [otlp]
      exporters: []
    metrics:
      receivers: [otlp]
      exporters: [debug,prometheusremotewrite]
    logs:
      receivers: [otlp]
      exporters: []
```