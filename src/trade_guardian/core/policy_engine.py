from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from uuid import uuid4

from trade_guardian.core.schemas import (
    AuditBlock,
    EvaluationResponse,
    MarketSnapshot,
    PortfolioSnapshot,
    RiskBlock,
    RuleCheck,
    RuleSeverity,
    Side,
    SuggestedEdit,
    TradeIntent,
    Verdict,
    WarningItem,
    WarningSeverity,
)


@dataclass(slots=True)
class PolicyConfig:
    max_risk_pct_per_trade: float  # percent of NAV (e.g., 1.0 => 1%)
    max_daily_loss_pct: float  # percent of NAV
    max_trades_per_day: int
    cooldown_minutes_after_loss: int
    require_stop_loss: bool
    min_rr: float  # minimum risk:reward ratio
    max_symbol_concentration_pct: float  # percent of NAV
    max_spread_bps_warn: float = 30.0  # warn if spread exceeds this threshold


@dataclass(slots=True)
class PolicyContext:
    today_pnl: float  # USD
    trades_last_24h: int
    last_trade_was_loss: bool
    last_trade_time: Optional[datetime]
    open_positions_count: int
    symbol_concentration_pct: float  # existing symbol concentration in percent (0-100)


class PolicyEngine:
    def __init__(self, config: PolicyConfig) -> None:
        self.config = config

    def evaluate(
        self,
        intent: TradeIntent,
        market: MarketSnapshot,
        portfolio: PortfolioSnapshot,
        context: PolicyContext,
    ) -> EvaluationResponse:
        rule_checks: List[RuleCheck] = []
        warnings: List[WarningItem] = []
        suggested_edits: List[SuggestedEdit] = []

        max_loss_usd, max_loss_pct_nav = self._compute_max_loss(intent, market, portfolio)
        rr_estimate = self._compute_rr(intent, market)

        # R-STP-REQUIRED
        if self.config.require_stop_loss:
            has_stop = intent.stop_loss_price is not None
            rule_checks.append(
                RuleCheck(
                    rule_id="R-STP-REQUIRED",
                    **{"pass": has_stop},
                    severity=RuleSeverity.HIGH,
                    message="Stop loss must be provided" if not has_stop else "Stop present",
                )
            )

        # R-RISK-LIMIT
        risk_ok = max_loss_pct_nav <= self.config.max_risk_pct_per_trade if portfolio.nav_usd > 0 else True
        rule_checks.append(
            RuleCheck(
                rule_id="R-RISK-LIMIT",
                **{"pass": risk_ok},
                severity=RuleSeverity.HIGH,
                message=f"Max loss {max_loss_pct_nav:.3f}% NAV within limit {self.config.max_risk_pct_per_trade:.3f}%",
            )
        )

        # R-DD-LIMIT (daily loss)
        dd_pct = (-context.today_pnl / portfolio.nav_usd * 100.0) if portfolio.nav_usd > 0 and context.today_pnl < 0 else 0.0
        dd_ok = dd_pct <= self.config.max_daily_loss_pct
        rule_checks.append(
            RuleCheck(
                rule_id="R-DD-LIMIT",
                **{"pass": dd_ok},
                severity=RuleSeverity.HIGH,
                message=f"Today's drawdown {dd_pct:.3f}% within limit {self.config.max_daily_loss_pct:.3f}%",
            )
        )

        # R-TRADES-LIMIT
        trades_ok = context.trades_last_24h < self.config.max_trades_per_day
        rule_checks.append(
            RuleCheck(
                rule_id="R-TRADES-LIMIT",
                **{"pass": trades_ok},
                severity=RuleSeverity.MEDIUM,
                message=f"Trades in last 24h {context.trades_last_24h} < {self.config.max_trades_per_day}",
            )
        )

        # R-COOLDOWN
        cooldown_ok = True
        if context.last_trade_was_loss and context.last_trade_time is not None:
            now = datetime.now(timezone.utc)
            delta = now - context.last_trade_time
            cooldown_ok = delta >= timedelta(minutes=self.config.cooldown_minutes_after_loss)
        rule_checks.append(
            RuleCheck(
                rule_id="R-COOLDOWN",
                **{"pass": cooldown_ok},
                severity=RuleSeverity.HIGH,
                message="Cooldown requirement satisfied" if cooldown_ok else "In cooldown after last loss",
            )
        )

        # R-RR-MIN
        rr_ok = True if rr_estimate is None else rr_estimate >= self.config.min_rr
        rule_checks.append(
            RuleCheck(
                rule_id="R-RR-MIN",
                **{"pass": rr_ok},
                severity=RuleSeverity.MEDIUM,
                message="RR meets minimum" if rr_ok else f"RR {rr_estimate:.2f} below minimum {self.config.min_rr:.2f}" if rr_estimate is not None else "RR not computable",
            )
        )
        if rr_estimate is not None and rr_estimate < self.config.min_rr:
            warnings.append(
                WarningItem(severity=WarningSeverity.WARNING, message="Risk:Reward is below policy minimum")
            )

        # R-CONCENTRATION
        current_symbol_conc_pct = context.symbol_concentration_pct
        proposed_conc_pct = self._compute_proposed_concentration_pct(intent, market, portfolio, current_symbol_conc_pct)
        conc_ok = proposed_conc_pct <= self.config.max_symbol_concentration_pct
        rule_checks.append(
            RuleCheck(
                rule_id="R-CONCENTRATION",
                **{"pass": conc_ok},
                severity=RuleSeverity.HIGH,
                message=f"Proposed concentration {proposed_conc_pct:.2f}% <= {self.config.max_symbol_concentration_pct:.2f}%",
            )
        )

        # R-SPREAD
        spread_ok = market.spread_bps <= self.config.max_spread_bps_warn
        rule_checks.append(
            RuleCheck(
                rule_id="R-SPREAD",
                **{"pass": spread_ok},
                severity=RuleSeverity.MEDIUM,
                message=f"Spread {market.spread_bps:.1f} bps <= {self.config.max_spread_bps_warn:.1f} bps",
            )
        )
        if not spread_ok:
            warnings.append(WarningItem(severity=WarningSeverity.WARNING, message="Wide spread observed"))

        # Verdict and score
        verdict = self._compute_verdict(rule_checks)
        score = self._compute_score(rule_checks)

        risk = RiskBlock(
            max_loss_usd=max_loss_usd,
            max_loss_pct_nav=max_loss_pct_nav,
            rr_estimate=rr_estimate,
        )

        audit = AuditBlock(
            evaluation_id=uuid4(),
            inputs_hash="",
            created_at=datetime.now(timezone.utc),
        )

        return EvaluationResponse(
            verdict=verdict,
            score=score,
            risk=risk,
            rule_checks=rule_checks,
            warnings=warnings,
            suggested_edits=suggested_edits,
            questions=[],
            audit=audit,
        )

    def _compute_max_loss(self, intent: TradeIntent, market: MarketSnapshot, portfolio: PortfolioSnapshot) -> Tuple[float, float]:
        if portfolio.nav_usd <= 0:
            return 0.0, 0.0

        if intent.stop_loss_price is None:
            return 0.0, 0.0

        price = market.price
        stop = intent.stop_loss_price
        base_qty = (intent.size / price) if intent.size_type.name == "USD" else intent.size

        if intent.side == Side.BUY:
            per_unit_loss = max(0.0, price - stop)
        else:
            per_unit_loss = max(0.0, stop - price)

        loss_usd = per_unit_loss * base_qty
        pct_nav = (loss_usd / portfolio.nav_usd) * 100.0
        return loss_usd, pct_nav

    def _compute_rr(self, intent: TradeIntent, market: MarketSnapshot) -> Optional[float]:
        if intent.stop_loss_price is None or intent.take_profit_price is None:
            return None
        price = market.price
        stop = intent.stop_loss_price
        tp = intent.take_profit_price

        if intent.side == Side.BUY:
            risk = max(0.0, price - stop)
            reward = max(0.0, tp - price)
        else:
            risk = max(0.0, stop - price)
            reward = max(0.0, price - tp)

        if risk <= 0.0:
            return None
        return reward / risk if reward > 0.0 else 0.0

    def _compute_proposed_concentration_pct(
        self,
        intent: TradeIntent,
        market: MarketSnapshot,
        portfolio: PortfolioSnapshot,
        current_symbol_conc_pct: float,
    ) -> float:
        if portfolio.nav_usd <= 0:
            return current_symbol_conc_pct
        notional = intent.size if intent.size_type.name == "USD" else intent.size * market.price
        added_pct = (notional / portfolio.nav_usd) * 100.0
        return current_symbol_conc_pct + added_pct

    @staticmethod
    def _compute_verdict(checks: List[RuleCheck]) -> Verdict:
        has_red = any((not c.passed) and c.severity == RuleSeverity.HIGH for c in checks)
        has_yellow = any((not c.passed) and c.severity != RuleSeverity.HIGH for c in checks)
        if has_red:
            return Verdict.RED
        if has_yellow:
            return Verdict.YELLOW
        return Verdict.GREEN

    @staticmethod
    def _compute_score(checks: List[RuleCheck]) -> int:
        total = len(checks)
        if total == 0:
            return 100
        passed = sum(1 for c in checks if c.passed)
        return int(round(100 * passed / total))


