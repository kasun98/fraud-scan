import json
import logging
import os
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool

logger = logging.getLogger("database")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:localdev@localhost:5432/fraud_db"
)

_pool: ThreadedConnectionPool | None = None


def get_pool() -> ThreadedConnectionPool:
    global _pool
    if _pool is None:
        _pool = ThreadedConnectionPool(minconn=2, maxconn=10, dsn=DATABASE_URL)
        logger.info("Postgres connection pool created")
    return _pool

def save_decision(decision: dict) -> None:
    pool = get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO fraud_decisions (
                    transaction_id, user_id, amount, currency,
                    merchant_name, merchant_category, merchant_country,
                    user_country, payment_method, channel,
                    ml_score, rules_score, final_score,
                    decision, triggered_rules, is_fraud,
                    fraud_pattern, raw_transaction
                ) VALUES (
                    %(transaction_id)s, %(user_id)s, %(amount)s, %(currency)s,
                    %(merchant_name)s, %(merchant_category)s, %(merchant_country)s,
                    %(user_country)s, %(payment_method)s, %(channel)s,
                    %(ml_score)s, %(rules_score)s, %(final_score)s,
                    %(decision)s, %(triggered_rules)s, %(is_fraud)s,
                    %(fraud_pattern)s, %(raw_transaction)s
                )
                ON CONFLICT (transaction_id) DO NOTHING
            """, {
                "transaction_id":   decision.get("transaction_id"),
                "user_id":          decision.get("user_id", "unknown"),
                "amount":           decision.get("amount", 0.0),
                "currency":         decision.get("currency", "USD"),
                "merchant_name":    decision.get("merchant_name", ""),
                "merchant_category":decision.get("merchant_category", ""),
                "merchant_country": decision.get("merchant_country", ""),
                "user_country":     decision.get("user_country", ""),
                "payment_method":   decision.get("payment_method", ""),
                "channel":          decision.get("channel", ""),
                "ml_score":         decision.get("ml_score", 0.0),
                "rules_score":      decision.get("rules_score", 0.0),
                "final_score":      decision.get("final_score", 0.0),
                "decision":         decision.get("decision", "APPROVE"),
                "triggered_rules":  json.dumps(decision.get("triggered_rules", [])),
                "is_fraud":         decision.get("is_fraud", False),
                "fraud_pattern":    decision.get("fraud_pattern", ""),
                "raw_transaction":  json.dumps(decision.get("raw_transaction", {})),
            })
        conn.commit()
        logger.info("Saved decision %s ", decision.get("transaction_id"))
    except Exception as e:
        conn.rollback()
        logger.error("Failed to save decision: %s", e, exc_info=True)
        raise
    finally:
        pool.putconn(conn)

def get_decisions(
    limit: int = 50,
    offset: int = 0,
    decision_filter: str | None = None,
    user_id: str | None = None,
) -> list[dict]:
    pool = get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            where_clauses = []
            params: list = []

            if decision_filter:
                where_clauses.append("decision = %s")
                params.append(decision_filter)
            if user_id:
                where_clauses.append("user_id = %s")
                params.append(user_id)

            where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

            cur.execute(f"""
                SELECT * FROM fraud_decisions
                {where_sql}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """, params + [limit, offset])

            return [dict(row) for row in cur.fetchall()]
    finally:
        pool.putconn(conn)


def get_decision_by_id(transaction_id: str) -> dict | None:
    pool = get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM fraud_decisions WHERE transaction_id = %s",
                (transaction_id,)
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        pool.putconn(conn)


def save_review(review: dict) -> None:
    pool = get_pool()
    conn = pool.getconn()
    try:
        # Using a single context manager for both operations
        with conn.cursor() as cur:
            # 1. Insert the review record into history
            cur.execute("""
                INSERT INTO case_reviews
                    (transaction_id, analyst_id, analyst_decision, notes)
                VALUES
                    (%(transaction_id)s, %(analyst_id)s, %(analyst_decision)s, %(notes)s)
            """, review)

            # 2. Update status AND the is_fraud boolean in the main table
            cur.execute("""
                UPDATE fraud_decisions
                SET 
                    decision = %(analyst_decision)s,
                    is_fraud = CASE 
                        WHEN %(analyst_decision)s = 'CONFIRMED_FRAUD' THEN TRUE 
                        ELSE FALSE 
                    END,
                    updated_at = NOW()
                WHERE transaction_id = %(transaction_id)s::uuid
            """, review)
            
        # One commit for both operations ensures "all or nothing"
        conn.commit()
        logger.info("Review saved and is_fraud updated for tx %s", review.get("transaction_id"))
        
    except Exception as e:
        conn.rollback()
        logger.error("Failed to save review: %s", e)
        raise
    finally:
        pool.putconn(conn)


def get_stats() -> dict:
    pool = get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    COUNT(*)                                        AS total,
                    COUNT(*) FILTER (WHERE decision = 'APPROVE')   AS approved,
                    COUNT(*) FILTER (WHERE decision = 'REVIEW')    AS review,
                    COUNT(DISTINCT transaction_id) FILTER (WHERE decision IN ('BLOCK', 'CONFIRMED_FRAUD')) AS blocked,
                    COUNT(*) FILTER (WHERE is_fraud = TRUE)        AS fraud_total,
                    ROUND(AVG(final_score)::numeric, 4)            AS avg_score,
                    ROUND(AVG(amount)::numeric, 2)                 AS avg_amount,
                    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour') AS last_hour
                FROM fraud_decisions
            """)
            row = dict(cur.fetchone())
            row["avg_score"]         = float(row["avg_score"]         or 0)
            row["avg_amount"]        = float(row["avg_amount"]        or 0)
            return row
    finally:
        pool.putconn(conn)
