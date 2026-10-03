"""BriefFlow unit economics. ALL inputs are ASSUMPTION / 待验证.

LOW/BASE/HIGH mean low/base/high commercial performance, not measured forecasts.
Costs and ARPU use all monthly active users (free and paid) as denominator.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil, isfinite
from pathlib import Path
import warnings


@dataclass(frozen=True)
class Scenario:
    pro_price: float
    paid_conversion_rate: float
    full_llm_tokens_per_run: int
    module_replacement_ratio: float
    llm_rmb_per_million_tokens: float
    search_api_rmb_per_run: float
    storage_bandwidth_rmb_per_user_month: float
    notification_rmb_per_user_month: float
    fixed_server_rmb_per_month: float
    domain_rmb_per_year: float
    runs_per_user_month: int
    monthly_active_users: int

    def __post_init__(self) -> None:
        for name, value in vars(self).items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and nonnegative")
        for name in ("paid_conversion_rate", "module_replacement_ratio"):
            if getattr(self, name) > 1:
                raise ValueError(f"{name} must be between 0 and 1")
        for name in ("full_llm_tokens_per_run", "runs_per_user_month", "monthly_active_users"):
            if type(getattr(self, name)) is not int:
                raise ValueError(f"{name} must be an integer")


SCENARIOS: dict[str, Scenario] = {
    "low": Scenario(
        pro_price=19.0,  # ASSUMPTION — TO BE VALIDATED
        paid_conversion_rate=0.03,  # ASSUMPTION — TO BE VALIDATED
        full_llm_tokens_per_run=12000,  # ASSUMPTION — TO BE VALIDATED
        module_replacement_ratio=0.40,  # ASSUMPTION — TO BE VALIDATED
        llm_rmb_per_million_tokens=20.0,  # ASSUMPTION — TO BE VALIDATED
        search_api_rmb_per_run=0.03,  # ASSUMPTION — TO BE VALIDATED
        storage_bandwidth_rmb_per_user_month=0.0,  # ASSUMPTION — TO BE VALIDATED (GitHub Pages MVP)
        notification_rmb_per_user_month=0.05,  # ASSUMPTION — TO BE VALIDATED
        fixed_server_rmb_per_month=100.0,  # ASSUMPTION — TO BE VALIDATED
        domain_rmb_per_year=120.0,  # ASSUMPTION — TO BE VALIDATED
        runs_per_user_month=8,  # ASSUMPTION — TO BE VALIDATED
        monthly_active_users=100,  # ASSUMPTION — TO BE VALIDATED
    ),
    "base": Scenario(
        pro_price=29.0,  # ASSUMPTION — TO BE VALIDATED
        paid_conversion_rate=0.08,  # ASSUMPTION — TO BE VALIDATED
        full_llm_tokens_per_run=10000,  # ASSUMPTION — TO BE VALIDATED
        module_replacement_ratio=0.60,  # ASSUMPTION — TO BE VALIDATED
        llm_rmb_per_million_tokens=15.0,  # ASSUMPTION — TO BE VALIDATED
        search_api_rmb_per_run=0.02,  # ASSUMPTION — TO BE VALIDATED
        storage_bandwidth_rmb_per_user_month=0.0,  # ASSUMPTION — TO BE VALIDATED (GitHub Pages MVP)
        notification_rmb_per_user_month=0.03,  # ASSUMPTION — TO BE VALIDATED
        fixed_server_rmb_per_month=60.0,  # ASSUMPTION — TO BE VALIDATED
        domain_rmb_per_year=120.0,  # ASSUMPTION — TO BE VALIDATED
        runs_per_user_month=6,  # ASSUMPTION — TO BE VALIDATED
        monthly_active_users=300,  # ASSUMPTION — TO BE VALIDATED
    ),
    "high": Scenario(
        pro_price=39.0,  # ASSUMPTION — TO BE VALIDATED
        paid_conversion_rate=0.12,  # ASSUMPTION — TO BE VALIDATED
        full_llm_tokens_per_run=8000,  # ASSUMPTION — TO BE VALIDATED
        module_replacement_ratio=0.75,  # ASSUMPTION — TO BE VALIDATED
        llm_rmb_per_million_tokens=10.0,  # ASSUMPTION — TO BE VALIDATED
        search_api_rmb_per_run=0.01,  # ASSUMPTION — TO BE VALIDATED
        storage_bandwidth_rmb_per_user_month=0.0,  # ASSUMPTION — TO BE VALIDATED (GitHub Pages MVP)
        notification_rmb_per_user_month=0.02,  # ASSUMPTION — TO BE VALIDATED
        fixed_server_rmb_per_month=30.0,  # ASSUMPTION — TO BE VALIDATED
        domain_rmb_per_year=120.0,  # ASSUMPTION — TO BE VALIDATED
        runs_per_user_month=4,  # ASSUMPTION — TO BE VALIDATED
        monthly_active_users=600,  # ASSUMPTION — TO BE VALIDATED
    ),
}


def calculate_token_cost(tokens: float, rmb_per_million_tokens: float) -> float:
    """Return RMB per run using an assumed blended input/output token price."""
    if not all(isfinite(x) and x >= 0 for x in (tokens, rmb_per_million_tokens)):
        raise ValueError("Tokens and token price must be finite and nonnegative")
    return tokens * rmb_per_million_tokens / 1_000_000


def calculate_variable_cost_per_user(s: Scenario, architecture: str = "modular") -> float:
    """Return RMB per active user per month; run costs scale with usage."""
    if architecture not in {"full", "modular"}:
        raise ValueError("architecture must be full or modular")
    tokens = s.full_llm_tokens_per_run * (1 - s.module_replacement_ratio if architecture == "modular" else 1)
    return (calculate_token_cost(tokens, s.llm_rmb_per_million_tokens) + s.search_api_rmb_per_run) * s.runs_per_user_month + s.notification_rmb_per_user_month + s.storage_bandwidth_rmb_per_user_month


def calculate_arpu(s: Scenario) -> float:
    """Return monthly revenue per active user, including free users."""
    return s.pro_price * s.paid_conversion_rate


def calculate_contribution_margin(arpu: float, variable_cost: float) -> float:
    """Return contribution in RMB per active user per month (not a percentage)."""
    return arpu - variable_cost


def calculate_break_even_users(monthly_fixed_cost: float, contribution_margin: float) -> int | None:
    """Ceil fixed cost / margin to whole active users; warn if margin <= 0."""
    if not isfinite(monthly_fixed_cost) or monthly_fixed_cost < 0 or not isfinite(contribution_margin):
        raise ValueError("Fixed cost must be nonnegative and inputs finite")
    if contribution_margin <= 0:
        warnings.warn("无法达到盈亏平衡：Contribution Margin <= 0", RuntimeWarning, stacklevel=2)
        return None
    return ceil(monthly_fixed_cost / contribution_margin)


def calculate_token_saving_rate(full_tokens: float, modular_tokens: float) -> float:
    """Return fractional token savings; a zero/zero workload has zero savings."""
    if not all(isfinite(x) for x in (full_tokens, modular_tokens)) or not 0 <= modular_tokens <= full_tokens:
        raise ValueError("Require 0 <= modular_tokens <= full_tokens, both finite")
    return (full_tokens - modular_tokens) / full_tokens if full_tokens else 0.0


def calculate_metrics(s: Scenario) -> dict[str, float | int | None]:
    """Compare architectures at identical usage, users, revenue and fixed costs."""
    full = calculate_variable_cost_per_user(s, "full")
    modular = calculate_variable_cost_per_user(s)
    arpu = calculate_arpu(s)
    full_margin = calculate_contribution_margin(arpu, full)
    margin = calculate_contribution_margin(arpu, modular)
    fixed = s.fixed_server_rmb_per_month + s.domain_rmb_per_year / 12
    tokens = s.full_llm_tokens_per_run * (1 - s.module_replacement_ratio)
    return {
        **vars(s), "modular_tokens": tokens, "arpu": arpu,
        "variable_full": full, "variable_modular": modular,
        "margin_full": full_margin, "margin_modular": margin, "fixed": fixed,
        "break_even_full": calculate_break_even_users(fixed, full_margin),
        "break_even_modular": calculate_break_even_users(fixed, margin),
        "token_saving": calculate_token_saving_rate(s.full_llm_tokens_per_run, tokens),
        "monthly_cost_full": fixed + full * s.monthly_active_users,
        "monthly_cost_modular": fixed + modular * s.monthly_active_users,
        "monthly_cost_saving": (full - modular) * s.monthly_active_users,
        "margin_difference": margin - full_margin,
    }


def generate_report(path: Path) -> str:
    """Generate the report directly from configuration and calculations."""
    metrics = [calculate_metrics(s) for s in SCENARIOS.values()]
    rows = [
        ("Pro Price (RMB/month)", "pro_price", False),
        ("Paid Conversion Rate", "paid_conversion_rate", True),
        ("Full LLM Tokens / Run", "full_llm_tokens_per_run", False),
        ("Modular Tokens / Run", "modular_tokens", False),
        ("Module Replacement Ratio", "module_replacement_ratio", True),
        ("LLM Cost / 1M Tokens (RMB)", "llm_rmb_per_million_tokens", False),
        ("Search/API Cost (RMB/run)", "search_api_rmb_per_run", False),
        ("Storage/Bandwidth (RMB/user/month)", "storage_bandwidth_rmb_per_user_month", False),
        ("Notification (RMB/user/month)", "notification_rmb_per_user_month", False),
        ("Server (RMB/month)", "fixed_server_rmb_per_month", False),
        ("Domain (RMB/year)", "domain_rmb_per_year", False),
        ("Runs / User / Month", "runs_per_user_month", False),
        ("Monthly Active Users", "monthly_active_users", False),
        ("Variable Cost / User — Full (RMB/month)", "variable_full", False),
        ("Variable Cost / User — Modular (RMB/month)", "variable_modular", False),
        ("ARPU (RMB/month)", "arpu", False),
        ("Contribution Margin — Full (RMB/user/month)", "margin_full", False),
        ("Contribution Margin — Modular (RMB/user/month)", "margin_modular", False),
        ("Fixed Cost (RMB/month, server + domain/12)", "fixed", False),
        ("Break-even Users — Full", "break_even_full", False),
        ("Break-even Users — Modular", "break_even_modular", False),
        ("Token Saving Rate", "token_saving", True),
        ("Monthly Cost — Full (RMB)", "monthly_cost_full", False),
        ("Monthly Cost — Modular (RMB)", "monthly_cost_modular", False),
        ("Monthly Cost Saving (RMB)", "monthly_cost_saving", False),
        ("Contribution Margin Difference (RMB/user/month)", "margin_difference", False),
    ]
    lines = ["# BriefFlow Unit Economics", "", "ASSUMPTION / 待验证：全部输入为占位假设，计算结果也不是实测数据。", "", "LOW / BASE / HIGH 表示商业表现情景；每用户指全部月活用户（含免费用户）。", "月成本按各情景月活及运行频次计算；架构间仅改变 Token 用量，其余条件相同。", "金额为人民币。盈亏平衡人数向上取整；非正贡献毛利返回 None 并警告。", "", "| Metric | Low | Base | High | Source / Status |", "|---|---:|---:|---:|---|"]
    for label, key, percent in rows:
        values = []
        for m in metrics:
            value = m[key]
            values.append("无法达到盈亏平衡" if value is None else (f"{value:.1%}" if percent else f"{value:,.2f}"))
        lines.append(f"| {label} | {' | '.join(values)} | 假设值，待验证 |")
    lines += ["", "确定性 Python 负责日期判断、关键词过滤、去重、基础排序、规则匹配、网页格式化和静态生成；LLM 负责自然语言理解、语义分类、语义匹配、摘要和解释。替代比例是待测假设，并非已实现或已测性能。", "", "MVP 假设 GitHub Pages 存储/带宽变量成本为零；LLM 单价是输入/输出混合占位单价，不是供应商报价。未包含人工、获客、税费、支付手续费；此处盈亏平衡仅覆盖列出的技术成本。", "", "2026-10-07 测试后更新：价格接受度、付费意愿与后续实际转化率、月活与使用频次、两种架构 Token 和质量、API 调用费用、通知费用、存储带宽、服务器与域名成本。单日测试不能证明长期转化率或月度留存。", ""]
    report = "\n".join(lines)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")
    return report


if __name__ == "__main__":
    print(generate_report(Path(__file__).resolve().parent / "outputs" / "unit_economics_output.md"))
