FROM python:3.12-bullseye

RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

RUN apt-get update

COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt --no-cache-dir

COPY . .

RUN chown -R appuser:appuser /app
RUN chmod +x ./scripts/entrypoint_api.sh

USER appuser

EXPOSE 8000

CMD ["./scripts/entrypoint_api.sh"]
