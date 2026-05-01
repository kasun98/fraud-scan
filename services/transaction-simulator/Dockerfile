FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    kafka-python-ng==2.2.3 \
    jsonschema==4.23.0

COPY config.py .
COPY src/ ./src/
COPY schemas/ ./schemas/

ENV PYTHONPATH=/app:/app/src
ENV PYTHONUNBUFFERED=1

CMD ["python", "src/main.py"]