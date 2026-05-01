import os

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC_RAW         = os.getenv("KAFKA_TOPIC_RAW", "transactions-raw")
TRANSACTIONS_PER_SECOND = float(os.getenv("TRANSACTIONS_PER_SECOND", "10"))
FRAUD_RATE              = float(os.getenv("FRAUD_RATE", "0.005"))   # 0.5%
LOG_LEVEL               = os.getenv("LOG_LEVEL", "INFO")