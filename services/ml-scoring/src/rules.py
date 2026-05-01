from dataclasses import dataclass
from typing import Any

HIGH_RISK_COUNTRIES = {"NG", "RU", "BY", "KP", "IR", "VE", "MM"}
HIGH_RISK_CATEGORIES = {"crypto", "gambling", "money_transfer", "gift_cards"}

# Known bad merchant IDs (in production, loaded from a database)
BAD_MERCHANT_IDS = {"merch-bad-001", "merch-bad-002"}


@dataclass
class RuleResult:
    triggered:   bool
    rule_name:   str
    reason:      str
    risk_score:  float      # 0.0 to 1.0 additive contribution


def evaluate_all_rules(features: dict[str, Any], velocity: int) -> list[RuleResult]:
    results = []

    # Rule 1 — Velocity: more than 10 transactions in 10 minutes
    if velocity > 10:
        results.append(RuleResult(
            triggered=True,
            rule_name="high_velocity",
            reason=f"{velocity} transactions in 10 minutes (threshold: 10)",
            risk_score=0.45,
        ))

    # Rule 2 — Impossible travel: high geo distance + recent transaction
    geo_km           = features.get("geo_distance_km", 0)
    hours_since_last = features.get("hours_since_last_txn", 99)
    if geo_km > 3000 and 0 < hours_since_last < 3:
        results.append(RuleResult(
            triggered=True,
            rule_name="impossible_travel",
            reason=f"Distance {geo_km:.0f}km in {hours_since_last:.1f}h",
            risk_score=0.7,
        ))

    # Rule 3 — High risk country
    if features.get("is_high_risk_country", 0) == 1:
        results.append(RuleResult(
            triggered=True,
            rule_name="high_risk_country",
            reason=f"Merchant country: {features.get('merchant_country')}",
            risk_score=0.2,
        ))

    # Rule 4 — Extreme amount spike
    amount_dev = features.get("amount_deviation", 0)
    if amount_dev > 10:
        results.append(RuleResult(
            triggered=True,
            rule_name="amount_spike",
            reason=f"Amount deviation: {amount_dev:.1f}x above baseline",
            risk_score=0.35,
        ))

    # Rule 5 — New device + large amount
    if features.get("is_new_device", 0) == 1 and features.get("amount", 0) > 5000:
        results.append(RuleResult(
            triggered=True,
            rule_name="new_device_large_amount",
            reason=f"New device with amount ${features.get('amount', 0):,.2f}",
            risk_score=0.7,
        ))

    # Rule 6 — High risk merchant category
    if features.get("merchant_category") in HIGH_RISK_CATEGORIES:
        results.append(RuleResult(
            triggered=True,
            rule_name="high_risk_category",
            reason=f"Category: {features.get('merchant_category')}",
            risk_score=0.15,
        ))

    # Rule 7 — Card testing: tiny amount on digital goods via API
    if (features.get("amount", 0) < 2.0
            and features.get("channel") == "api"
            and features.get("merchant_category") == "digital_goods"):
        results.append(RuleResult(
            triggered=True,
            rule_name="card_testing",
            reason=f"Micro amount ${features.get('amount')} via API on digital goods",
            risk_score=0.45,
        ))

    # Rule 8 — Known bad merchant
    if features.get("merchant_id") in BAD_MERCHANT_IDS:
        results.append(RuleResult(
            triggered=True,
            rule_name="bad_merchant",
            reason=f"Merchant {features.get('merchant_id')} on blocklist",
            risk_score=0.9,
        ))

    return results


def compute_rules_score(results: list[RuleResult]) -> float:
    """Combine rule scores — capped at 1.0."""
    total = sum(r.risk_score for r in results if r.triggered)
    return min(round(total, 4), 1.0)