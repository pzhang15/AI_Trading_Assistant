from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from trade_guardian.core.schemas import (
    AuditBlock,
    EvaluationResponse,
    MarketSnapshot,
    OrderType,
    PortfolioSnapshot,
    PositionSnapshot,
    RuleCheck,
    RuleSeverity,
    Side,
    SuggestedEdit,
    TimeHorizon,
    TradeIntent,
    Verdict,
    WarningItem,
    WarningSeverity,
    RiskBlock,
)
from trade_guardian.utils.hash import compute_inputs_hash


def _now() -> datetime:
    return datetime.now(timezone.utc)


def test_trade_intent_limit_price_required() -> None:
    with pytest.raises(ValidationError):
        TradeIntent(
            symbol="BTC-USD",
            side=Side.BUY,
            order_type=OrderType.LIMIT,
            size=100.0,
            size_type="USD",
            time_horizon=TimeHorizon.DAY,
            setup_name="Mean reversion",
            client_timestamp=_now(),
            request_id=uuid4(),
        )


def test_trade_intent_market_limit_price_forbidden() -> None:
    with pytest.raises(ValidationError):
        TradeIntent(
            symbol="BTC-USD",
            side=Side.BUY,
            order_type=OrderType.MARKET,
            limit_price=50000.0,
            size=0.01,
            size_type="BASE",
            time_horizon=TimeHorizon.SCALP,
            setup_name="Breakout",
            client_timestamp=_now(),
            request_id=uuid4(),
        )


def test_market_snapshot_validation() -> None:
    m = MarketSnapshot(
        price=100.0,
        spread_bps=5.0,
        vol_1h=1_000_000.0,
        vol_1d=10_000_000.0,
        liquidity_hint="deep",
        timestamp=_now(),
    )
    assert m.price == 100.0


def test_evaluation_response_round_trip() -> None:
    audit = AuditBlock(
        evaluation_id=uuid4(),
        inputs_hash="abc123",
        created_at=_now(),
    )
    resp = EvaluationResponse(
        verdict=Verdict.GREEN,
        score=87,
        risk=RiskBlock(max_loss_usd=250.0, max_loss_pct_nav=1.2, rr_estimate=2.5),
        rule_checks=[
            RuleCheck(rule_id="R-1", **{"pass": True}, severity=RuleSeverity.LOW, message="OK"),
            RuleCheck(rule_id="R-2", **{"pass": False}, severity=RuleSeverity.HIGH, message="Violation"),
        ],
        warnings=[WarningItem(severity=WarningSeverity.WARNING, message="Tight stop")],
        suggested_edits=[
            SuggestedEdit(field="size", proposed_value=50.0, reason="Reduce exposure"),
        ],
        questions=["What is the catalyst?"],
        audit=audit,
    )

    json_data = resp.model_dump_json()
    parsed = EvaluationResponse.model_validate_json(json_data)
    assert parsed == resp


def test_inputs_hash_is_deterministic() -> None:
    data_a = {"b": 2, "a": 1}
    data_b = {"a": 1, "b": 2}
    assert compute_inputs_hash(data_a) == compute_inputs_hash(data_b)


def test_portfolio_snapshot_and_positions() -> None:
    p = PortfolioSnapshot(
        nav_usd=10000.0,
        cash_usd=4000.0,
        positions=[
            PositionSnapshot(symbol="BTC-USD", qty=0.1, usd_value=3000.0),
            PositionSnapshot(symbol="ETH-USD", qty=1.0, usd_value=3000.0),
        ],
        exposure_by_symbol={"BTC-USD": 0.3, "ETH-USD": 0.3},
    )
    assert len(p.positions) == 2


