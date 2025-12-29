from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from trade_guardian.core.policy_engine import PolicyConfig, PolicyContext, PolicyEngine
from trade_guardian.core.schemas import (
    MarketSnapshot,
    PortfolioSnapshot,
    PositionSnapshot,
    Side,
    SizeType,
    TimeHorizon,
    TradeIntent,
    Verdict,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _base_env():
    market = MarketSnapshot(price=100.0, spread_bps=10.0, vol_1h=0.0, vol_1d=0.0, liquidity_hint=None, timestamp=_now())
    portfolio = PortfolioSnapshot(
        nav_usd=10000.0,
        cash_usd=5000.0,
        positions=[PositionSnapshot(symbol="BTC-USD", qty=0.0, usd_value=0.0)],
        exposure_by_symbol={"BTC-USD": 0.0},
    )
    context = PolicyContext(
        today_pnl=0.0,
        trades_last_24h=0,
        last_trade_was_loss=False,
        last_trade_time=None,
        open_positions_count=0,
        symbol_concentration_pct=0.0,
    )
    return market, portfolio, context


def _config() -> PolicyConfig:
    return PolicyConfig(
        max_risk_pct_per_trade=1.0,
        max_daily_loss_pct=5.0,
        max_trades_per_day=10,
        cooldown_minutes_after_loss=60,
        require_stop_loss=True,
        min_rr=2.0,
        max_symbol_concentration_pct=30.0,
        max_spread_bps_warn=30.0,
    )


def test_missing_stop_produces_red_when_required() -> None:
    cfg = _config()
    engine = PolicyEngine(cfg)
    market, portfolio, context = _base_env()

    intent = TradeIntent(
        symbol="BTC-USD",
        side=Side.BUY,
        order_type="MARKET",
        size=1000.0,
        size_type=SizeType.USD,
        time_horizon=TimeHorizon.DAY,
        setup_name="Test",
        client_timestamp=_now(),
        request_id=uuid4(),
    )

    resp = engine.evaluate(intent, market, portfolio, context)
    assert resp.verdict == Verdict.RED
    assert any(c.rule_id == "R-STP-REQUIRED" and not c.passed for c in resp.rule_checks)


def test_too_large_risk_produces_red() -> None:
    cfg = _config()
    engine = PolicyEngine(cfg)
    market, portfolio, context = _base_env()

    # With size $5000 and stop 5 dollars below for BUY at price 100 -> base_qty=50, loss=5*50=250, 2.5% of NAV
    intent = TradeIntent(
        symbol="BTC-USD",
        side=Side.BUY,
        order_type="MARKET",
        size=5000.0,
        size_type=SizeType.USD,
        stop_loss_price=95.0,
        time_horizon=TimeHorizon.DAY,
        setup_name="Risky",
        client_timestamp=_now(),
        request_id=uuid4(),
    )

    resp = engine.evaluate(intent, market, portfolio, context)
    assert resp.verdict == Verdict.RED
    assert any(c.rule_id == "R-RISK-LIMIT" and not c.passed for c in resp.rule_checks)


def test_min_rr_violation_yellow() -> None:
    cfg = _config()
    engine = PolicyEngine(cfg)
    market, portfolio, context = _base_env()

    # risk = 2 (100-98), reward = 2 (102-100) => rr=1.0 < min_rr=2.0
    intent = TradeIntent(
        symbol="BTC-USD",
        side=Side.BUY,
        order_type="MARKET",
        size=1000.0,
        size_type=SizeType.USD,
        stop_loss_price=98.0,
        take_profit_price=102.0,
        time_horizon=TimeHorizon.DAY,
        setup_name="RR Test",
        client_timestamp=_now(),
        request_id=uuid4(),
    )

    resp = engine.evaluate(intent, market, portfolio, context)
    assert resp.verdict == Verdict.YELLOW
    assert any(c.rule_id == "R-RR-MIN" and not c.passed for c in resp.rule_checks)


def test_cooldown_triggered_red() -> None:
    cfg = _config()
    engine = PolicyEngine(cfg)
    market, portfolio, _ = _base_env()
    context = PolicyContext(
        today_pnl=0.0,
        trades_last_24h=0,
        last_trade_was_loss=True,
        last_trade_time=_now() - timedelta(minutes=10),
        open_positions_count=0,
        symbol_concentration_pct=0.0,
    )

    intent = TradeIntent(
        symbol="BTC-USD",
        side=Side.BUY,
        order_type="MARKET",
        size=100.0,
        size_type=SizeType.USD,
        stop_loss_price=99.0,
        time_horizon=TimeHorizon.DAY,
        setup_name="Cooldown",
        client_timestamp=_now(),
        request_id=uuid4(),
    )

    resp = engine.evaluate(intent, market, portfolio, context)
    assert resp.verdict == Verdict.RED
    assert any(c.rule_id == "R-COOLDOWN" and not c.passed for c in resp.rule_checks)


