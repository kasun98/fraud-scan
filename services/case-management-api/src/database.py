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
    decision_filter: list[str] | None = None,
    user_id: str | None = None,
) -> list[dict]:
    pool = get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            where_clauses = []
            params: list = []

            if decision_filter:
                where_clauses.append("decision IN %s")
                params.append(tuple(decision_filter))
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
                    (SELECT COUNT(*) FROM fraud_decisions) AS total,
                    (SELECT COUNT(*) FROM fraud_decisions WHERE decision = 'REVIEW') AS review,
                    (SELECT COUNT(*) FROM fraud_decisions WHERE decision IN ('BLOCK', 'CONFIRMED_FRAUD')) AS blocked,
                    (SELECT SUM(amount) FROM fraud_decisions WHERE decision IN ('BLOCK', 'CONFIRMED_FRAUD')) AS fraud_value,
                    (SELECT SUM(amount) FROM fraud_decisions WHERE decision = 'APPROVE') AS safe_value,
                    (SELECT AVG(final_score) FROM fraud_decisions) AS avg_score
            """)
            row = dict(cur.fetchone())
            return {
                "total": row["total"] or 0,
                "review": row["review"] or 0,
                "blocked": row["blocked"] or 0,
                "fraud_value": float(row["fraud_value"] or 0),
                "safe_value": float(row["safe_value"] or 0),
                "avg_score": float(row["avg_score"] or 0)
            }
    finally:
        pool.putconn(conn)

def get_chart_data() -> list[dict]:
    pool = get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    TO_CHAR(DATE(created_at), 'Mon DD') as date,
                    COUNT(*) as transactions,
                    AVG(final_score) as score,
                    SUM(amount) as total_amount,
                    SUM(CASE WHEN decision IN ('BLOCK', 'CONFIRMED_FRAUD') THEN amount ELSE 0 END) as fraud_amount,
                    COUNT(CASE WHEN decision IN ('BLOCK', 'CONFIRMED_FRAUD') THEN 1 END) as blocked_count,
                    COUNT(CASE WHEN decision = 'APPROVE' THEN 1 END) as approved_count,
                    COUNT(CASE WHEN decision = 'REVIEW' THEN 1 END) as review_count
                FROM fraud_decisions
                GROUP BY DATE(created_at)
                ORDER BY DATE(created_at) ASC
                LIMIT 30
            """)
            rows = cur.fetchall()
            return [{
                "date": r["date"],
                "transactions": r["transactions"],
                "score": float(r["score"] or 0),
                "total_amount": float(r["total_amount"] or 0),
                "fraud_amount": float(r["fraud_amount"] or 0),
                "blocked_count": r["blocked_count"],
                "approved_count": r["approved_count"],
                "review_count": r["review_count"]
            } for r in rows]
    finally:
        pool.putconn(conn)

def get_map_data() -> list[dict]:
    pool = get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    user_country as country,
                    SUM(amount) as fraud_amount,
                    COUNT(*) as fraud_count
                FROM fraud_decisions
                WHERE decision IN ('BLOCK', 'CONFIRMED_FRAUD') AND user_country IS NOT NULL AND user_country != ''
                  AND DATE(created_at) = CURRENT_DATE
                GROUP BY user_country
                ORDER BY fraud_amount DESC
            """)
            rows = cur.fetchall()
            return [{
                "country": r["country"],
                "fraud_amount": float(r["fraud_amount"] or 0),
                "fraud_count": r["fraud_count"]
            } for r in rows]
    finally:
        pool.putconn(conn)
