FROM tiangolo/uvicorn-gunicorn-fastapi:python3.11-2024-04-08
RUN apt update
RUN apt-get install vim -y
RUN apt-get install lsof -y

RUN apt-get update && apt-get install -y apt-transport-https ca-certificates curl gnupg && \
    curl -sLf --retry 3 --tlsv1.2 --proto "=https" 'https://packages.doppler.com/public/cli/gpg.DE2A7741A397C129.key' | apt-key add - && \
    echo "deb https://packages.doppler.com/public/cli/deb/debian any-version main" | tee /etc/apt/sources.list.d/doppler-cli.list && \
    apt-get update && \
    apt-get -y install doppler

WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt

EXPOSE 5000
CMD ["doppler", "run", "--", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "5000", "--log-config", "log.ini"]