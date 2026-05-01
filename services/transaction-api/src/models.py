from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class PaymentMethod(str, Enum):
    credit_card    = "credit_card"
    debit_card     = "debit_card"
    bank_transfer  = "bank_transfer"
    digital_wallet = "digital_wallet"
    crypto         = "crypto"


class Channel(str, Enum):
    web    = "web"
    mobile = "mobile"
    atm    = "atm"
    pos    = "pos"
    api    = "api"


class EventType(str, Enum):
    initiated = "transaction.initiated"
    completed = "transaction.completed"
    failed    = "transaction.failed"


class TransactionEvent(BaseModel):
    transaction_id:    UUID
    user_id:           str            = Field(..., min_length=1, max_length=64)
    session_id:        str | None     = None
    amount:            float          = Field(..., gt=0, le=1_000_000)
    currency:          str            = Field(..., pattern=r"^[A-Z]{3}$")
    merchant_id:       str
    merchant_name:     str
    merchant_category: str
    merchant_country:  str            = Field(..., pattern=r"^[A-Z]{2}$")
    user_country:      str            = Field(..., pattern=r"^[A-Z]{2}$")
    user_city:         str | None     = None
    latitude:          float | None   = Field(None, ge=-90,  le=90)
    longitude:         float | None   = Field(None, ge=-180, le=180)
    payment_method:    PaymentMethod
    channel:           Channel
    device_id:         str | None     = None
    ip_address:        str | None     = None
    timestamp:         datetime
    event_type:        EventType
    metadata:          dict[str, Any] = Field(default_factory=dict)

    @field_validator("amount")
    @classmethod
    def round_amount(cls, v: float) -> float:
        return round(v, 2)

    def to_kafka_payload(self) -> dict[str, Any]:
        data = self.model_dump()
        data["transaction_id"] = str(data["transaction_id"])
        data["timestamp"]      = self.timestamp.isoformat()
        data["payment_method"] = self.payment_method.value
        data["channel"]        = self.channel.value
        data["event_type"]     = self.event_type.value
        data["is_fraud"]       = False
        data["fraud_pattern"]  = None
        return data


class TransactionResponse(BaseModel):
    transaction_id: str
    status:         str
    topic:          str
    partition:      int
    offset:         int
    message:        str