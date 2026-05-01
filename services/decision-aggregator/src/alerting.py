import json
import logging
import os
from datetime import datetime, timezone

import urllib.request
import urllib.error

logger = logging.getLogger("alerting")

SENDGRID_API_KEY   = os.getenv("SENDGRID_API_KEY", "")
ALERT_EMAIL_TO     = os.getenv("ALERT_EMAIL_TO", "")
ALERT_EMAIL_FROM   = os.getenv("ALERT_EMAIL_FROM", "alerts@fraud-detection.local")
WEBHOOK_URL        = os.getenv("ALERT_WEBHOOK_URL", "")


def send_email_alert(decision: dict) -> bool:
    if not SENDGRID_API_KEY or not ALERT_EMAIL_TO:
        logger.debug("Email alerting not configured — skipping")
        return False

    subject = f"[FRAUD ALERT] {decision['decision']} — ${decision['amount']:,.2f} — {decision['transaction_id']}"
    body = f"""
Fraud Detection Alert
=====================
Transaction ID : {decision['transaction_id']}
User ID        : {decision['user_id']}
Amount         : ${decision['amount']:,.2f}
Decision       : {decision['decision']}
ML Score       : {decision['ml_score']:.4f}
Rules Score    : {decision['rules_score']:.4f}
Final Score    : {decision['final_score']:.4f}
Triggered Rules: {', '.join(decision.get('triggered_rules', []))}
Merchant       : {decision.get('merchant_name', 'N/A')}
Timestamp      : {datetime.now(timezone.utc).isoformat()}
"""
    payload = json.dumps({
        "personalizations": [{"to": [{"email": ALERT_EMAIL_TO}]}],
        "from":             {"email": ALERT_EMAIL_FROM},
        "subject":          subject,
        "content":          [{"type": "text/plain", "value": body}],
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.sendgrid.com/v3/mail/send",
        data=payload,
        headers={
            "Authorization": f"Bearer {SENDGRID_API_KEY}",
            "Content-Type":  "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            logger.info("Email alert sent for %s", decision['transaction_id'])
            return True
    except urllib.error.URLError as e:
        logger.error("Email alert failed: %s", e)
        return False


def send_webhook_alert(decision: dict) -> bool:
    if not WEBHOOK_URL:
        logger.debug("Webhook not configured — skipping")
        return False

    payload = json.dumps({
        "event":          "fraud.detected",
        "transaction_id": decision["transaction_id"],
        "user_id":        decision["user_id"],
        "amount":         decision["amount"],
        "decision":       decision["decision"],
        "final_score":    decision["final_score"],
        "triggered_rules": decision.get("triggered_rules", []),
        "timestamp":      datetime.now(timezone.utc).isoformat(),
    }).encode("utf-8")

    req = urllib.request.Request(
        WEBHOOK_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            logger.info("Webhook sent for %s", decision["transaction_id"])
            return True
    except urllib.error.URLError as e:
        logger.error("Webhook failed: %s", e)
        return False


def fire_alerts(decision: dict) -> None:
    """Fire all configured alerts for BLOCK decisions."""
    if decision.get("decision") != "BLOCK":
        return
    send_email_alert(decision)
    send_webhook_alert(decision)