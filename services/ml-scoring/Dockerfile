FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir setuptools==75.0.0 && \
    pip install --no-cache-dir \
    fastapi==0.115.0 \
    uvicorn[standard]==0.30.0 \
    kafka-python-ng==2.2.3 \
    xgboost==2.1.0 \
    scikit-learn==1.5.0 \
    pandas==2.2.0 \
    numpy==1.26.0

COPY src/ ./src/
COPY model/ ./model/

ENV PYTHONPATH=/app:/app/src
ENV MODEL_PATH=/app/model/model.ubj
ENV FRAUD_THRESHOLD=0.5
ENV PYTHONUNBUFFERED=1

EXPOSE 8001

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]