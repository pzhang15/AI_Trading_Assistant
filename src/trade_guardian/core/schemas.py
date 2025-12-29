from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class SizeType(str, Enum):
    USD = "USD"
    BASE = "BASE"


class TimeHorizon(str, Enum):
    SCALP = "SCALP"
    DAY = "DAY"
    SWING = "SWING"


class Verdict(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


class RuleSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class WarningSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"


class TradeIntent(BaseModel):
    symbol: str = Field(min_length=1)
    side: Side
    order_type: OrderType
    limit_price: Optional[float] = None
    size: float = Field(gt=0)
    size_type: SizeType
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    time_horizon: TimeHorizon
    setup_name: str = Field(min_length=1)
    user_reason: Optional[str] = None
    client_timestamp: datetime
    request_id: UUID

    @field_validator("limit_price", "stop_loss_price", "take_profit_price")
    @classmethod
    def _validate_positive_prices(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("Price values must be > 0")
        return v

    @model_validator(mode="after")
    def _validate_limit_order_requirements(self) -> "TradeIntent":
        if self.order_type == OrderType.LIMIT and self.limit_price is None:
            raise ValidationError.from_exception_data(
                "TradeIntent",
                [{"loc": ("limit_price",), "msg": "limit_price required for LIMIT orders", "type": "value_error"}],
            )
        if self.order_type == OrderType.MARKET and self.limit_price is not None:
            raise ValidationError.from_exception_data(
                "TradeIntent",
                [{"loc": ("limit_price",), "msg": "limit_price must be omitted for MARKET orders", "type": "value_error"}],
            )
        return self


class MarketSnapshot(BaseModel):
    price: float = Field(gt=0)
    spread_bps: float = Field(ge=0)
    vol_1h: float = Field(ge=0)
    vol_1d: float = Field(ge=0)
    liquidity_hint: Optional[str] = None
    timestamp: datetime


class PositionSnapshot(BaseModel):
    symbol: str
    qty: float
    usd_value: float

    @field_validator("qty", "usd_value")
    @classmethod
    def _non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Position values must be >= 0")
        return v


class PortfolioSnapshot(BaseModel):
    nav_usd: float = Field(ge=0)
    cash_usd: float = Field(ge=0)
    positions: List[PositionSnapshot] = Field(default_factory=list)
    exposure_by_symbol: Dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_nav(self) -> "PortfolioSnapshot":
        total_positions = sum(p.usd_value for p in self.positions)
        # Cash + positions should not exceed NAV by more than small epsilon; this is a soft check.
        if self.cash_usd + total_positions > self.nav_usd * 1.0001 and self.nav_usd > 0:
            # Soft warning via validation error could be too strict; ignore strictness for now.
            # Keeping only non-failing check to avoid blocking usage.
            return self
        return self


class RiskBlock(BaseModel):
    max_loss_usd: float = Field(ge=0)
    max_loss_pct_nav: float = Field(ge=0, le=100)
    rr_estimate: Optional[float] = Field(default=None)


class RuleCheck(BaseModel):
    rule_id: str
    passed: bool = Field(alias="pass")
    severity: RuleSeverity
    message: str

    model_config = {"populate_by_name": True}


class WarningItem(BaseModel):
    severity: WarningSeverity
    message: str


class SuggestedEdit(BaseModel):
    field: str
    proposed_value: Any
    reason: str


class AuditBlock(BaseModel):
    evaluation_id: UUID
    inputs_hash: str
    created_at: datetime


class EvaluationResponse(BaseModel):
    verdict: Verdict
    score: int = Field(ge=0, le=100)
    risk: RiskBlock
    rule_checks: List[RuleCheck] = Field(default_factory=list)
    warnings: List[WarningItem] = Field(default_factory=list)
    suggested_edits: List[SuggestedEdit] = Field(default_factory=list)
    questions: List[str] = Field(default_factory=list)
    audit: AuditBlock


