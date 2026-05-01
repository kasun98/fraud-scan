FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi==0.115.0 \
    uvicorn[standard]==0.30.0 \
    psycopg2-binary==2.9.9 \
    pydantic==2.8.0

COPY src/ ./src/
COPY src/database.py ./src/database.py

ENV PYTHONPATH=/app:/app/src
ENV PYTHONUNBUFFERED=1

EXPOSE 8002

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8002"]