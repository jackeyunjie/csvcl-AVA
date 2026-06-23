"""
Generate a daily observer-style report for MT5 products.

The report intentionally focuses on "what to watch first" rather than trade
instructions. It can read a JSON snapshot exported by monitoring/trading code,
or use built-in sample data for layout review.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = BASE_DIR / "reports" / "daily"


@dataclass
class ProductCard:
    rank: int
    symbol: str
    name: str
    market: str
    theme: str
    state: str
    price: Optional[float] = None
    spread: Optional[float] = None
    confidence: Optional[float] = None
    exposure: Optional[float] = None
    note: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class Direction:
    title: str
    description: str
    tags: List[str]


@dataclass
class ReportData:
    date: str
    generated_at: str
    product_name: str
    universe_name: str
    total_products: int
    watch_count: int
    priority_count: int
    focus_text: str
    directions: List[Direction]
    watchlist: List[ProductCard]
    risk_metrics: Dict[str, Any]
    account: Dict[str, Any]
    alerts: List[Dict[str, Any]]


def _pct(value: Any, default: str = "0.00%") -> str:
    try:
        return f"{float(value) * 100:.2f}%"
    except (TypeError, ValueError):
        return default


def _money(value: Any, default: str = "-") -> str:
    try:
        return f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return default


def _fmt_number(value: Any, digits: int = 5, default: str = "-") -> str:
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return default


def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _load_json(path: Optional[Path]) -> Dict[str, Any]:
    if not path:
        return sample_payload()
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _normalize_card(item: Dict[str, Any], rank: int) -> ProductCard:
    signal = item.get("signal") or item.get("last_signal") or {}
    market_state = item.get("market_state") or item.get("state") or "等待确认"
    symbol = item.get("symbol") or signal.get("symbol") or f"SYMBOL{rank}"
    name = item.get("name") or item.get("display_name") or symbol
    signal_type = signal.get("signal_type") or signal.get("type") or item.get("signal_type")
    confidence = item.get("confidence", signal.get("confidence"))

    tags = [str(tag) for tag in _as_list(item.get("tags"))]
    if signal_type and signal_type not in tags:
        tags.append(str(signal_type))
    if market_state and market_state not in tags:
        tags.append(str(market_state))

    note = item.get("note") or item.get("reasoning") or signal.get("reasoning")
    if not note:
        note = "状态已进入观察区，先看延续性，再看是否需要进入策略复核。"

    return ProductCard(
        rank=rank,
        symbol=str(symbol),
        name=str(name),
        market=str(item.get("market") or item.get("broker") or "MT5"),
        theme=str(item.get("theme") or item.get("asset_class") or "外汇 / 差价合约"),
        state=str(market_state),
        price=item.get("price", item.get("mid", signal.get("entry_price"))),
        spread=item.get("spread"),
        confidence=confidence,
        exposure=item.get("exposure"),
        note=str(note),
        tags=tags[:5],
    )


def _infer_directions(cards: List[ProductCard], payload: Dict[str, Any]) -> List[Direction]:
    explicit = payload.get("directions")
    if isinstance(explicit, list) and explicit:
        return [
            Direction(
                title=str(item.get("title", "观察方向")),
                description=str(item.get("description", "")),
                tags=[str(tag) for tag in _as_list(item.get("tags"))],
            )
            for item in explicit[:3]
        ]

    grouped: Dict[str, List[ProductCard]] = {}
    for card in cards:
        grouped.setdefault(card.theme, []).append(card)

    directions = []
    descriptions = {
        "外汇": "主要观察美元、欧元、日元等主流货币对的趋势延续和波动收缩。",
        "贵金属": "优先看避险资产是否持续走强，以及点差和波动是否放大。",
        "指数": "适合观察风险偏好方向，不急于从单个指数下判断全局。",
        "能源": "重点看趋势和库存/供需事件后的延续性。",
    }

    for theme, theme_cards in sorted(grouped.items(), key=lambda kv: len(kv[1]), reverse=True)[:3]:
        title = theme
        matched_description = next(
            (text for key, text in descriptions.items() if key in theme),
            "同类品种集中出现观察信号，先看方向是否共振，再看单品种是否延续。",
        )
        directions.append(
            Direction(
                title=title,
                description=matched_description,
                tags=[card.symbol for card in theme_cards[:4]],
            )
        )

    while len(directions) < 3:
        fallback = [
            Direction("主流货币", "先看 EURUSD、GBPUSD、USDJPY 等主流品种是否同向。", ["EURUSD", "GBPUSD", "USDJPY"]),
            Direction("避险资产", "观察 XAUUSD 与美元指数相关方向是否稳定。", ["XAUUSD", "XAGUSD"]),
            Direction("股指与能源", "波动更大，只适合作为状态延续观察，不做孤立判断。", ["US500", "NAS100", "WTI"]),
        ]
        directions.append(fallback[len(directions)])

    return directions[:3]


def _normalize_payload(payload: Dict[str, Any]) -> ReportData:
    now = datetime.now()
    raw_watchlist = _as_list(payload.get("watchlist") or payload.get("products") or payload.get("symbols"))
    cards = [_normalize_card(item, index + 1) for index, item in enumerate(raw_watchlist)]

    if not cards:
        cards = [_normalize_card(item, index + 1) for index, item in enumerate(sample_payload()["watchlist"])]

    risk_metrics = payload.get("risk_metrics") or payload.get("monitor", {}).get("risk_metrics") or {}
    account = payload.get("account") or payload.get("account_info") or {}
    alerts = _as_list(payload.get("alerts") or payload.get("recent_alerts"))

    priority_count = len(
        [
            card
            for card in cards
            if (card.confidence is not None and float(card.confidence) >= 0.6)
            or any(tag in {"BUY", "SELL", "强趋势", "高波动"} for tag in card.tags)
        ]
    )

    focus_text = payload.get("focus_text")
    if not focus_text:
        top_themes = ", ".join(direction.title for direction in _infer_directions(cards, payload)[:2])
        focus_text = f"{top_themes} 更集中"

    return ReportData(
        date=str(payload.get("date") or now.strftime("%Y-%m-%d")),
        generated_at=str(payload.get("generated_at") or now.strftime("%Y-%m-%d %H:%M")),
        product_name=str(payload.get("product_name") or "MT5 普通投资者观察版"),
        universe_name=str(payload.get("universe_name") or "MT5 产品池"),
        total_products=int(payload.get("total_products") or len(cards)),
        watch_count=len(cards),
        priority_count=priority_count,
        focus_text=str(focus_text),
        directions=_infer_directions(cards, payload),
        watchlist=cards[:12],
        risk_metrics=risk_metrics,
        account=account,
        alerts=alerts[:6],
    )


def _render_tags(tags: Iterable[str]) -> str:
    return "".join(f'<span class="pill">{escape(tag)}</span>' for tag in tags)


def _render_direction(direction: Direction) -> str:
    return f"""
        <article class="card direction-card">
            <h3>{escape(direction.title)}</h3>
            <p>{escape(direction.description)}</p>
            <div class="pills">{_render_tags(direction.tags)}</div>
        </article>
    """


def _render_product(card: ProductCard) -> str:
    confidence = "-" if card.confidence is None else _pct(card.confidence)
    price_digits = 2 if any(key in card.symbol.upper() for key in ("XAU", "XAG", "US", "NAS", "WTI")) else 5
    spread = "-" if card.spread is None else _fmt_number(card.spread, 1)
    exposure = "-" if card.exposure is None else _money(card.exposure)
    price = _fmt_number(card.price, price_digits)

    return f"""
        <article class="card product-card">
            <div class="product-head">
                <div>
                    <h3>{escape(card.name)}</h3>
                    <div class="muted">{escape(card.symbol)} · {escape(card.market)} / {escape(card.theme)}</div>
                </div>
                <span class="rank">#{card.rank}</span>
            </div>
            <p>{escape(card.note)}</p>
            <div class="metrics two">
                <div><span>状态</span><strong>{escape(card.state)}</strong></div>
                <div><span>信号信心</span><strong>{confidence}</strong></div>
                <div><span>最新价格</span><strong>{price}</strong></div>
                <div><span>点差/敞口</span><strong>{spread} / {exposure}</strong></div>
            </div>
            <div class="pills">{_render_tags(card.tags)}</div>
        </article>
    """


def _render_alerts(alerts: List[Dict[str, Any]]) -> str:
    if not alerts:
        return """
            <article class="card step-card">
                <span>0</span>
                <h3>暂无风险提醒</h3>
                <p>今天没有需要单独展开的系统告警，继续观察状态是否延续。</p>
            </article>
        """

    items = []
    for index, alert in enumerate(alerts[:4], 1):
        level = str(alert.get("level", "INFO"))
        category = str(alert.get("category", "SYSTEM"))
        message = str(alert.get("message", "监控提醒"))
        items.append(
            f"""
            <article class="card step-card">
                <span>{index}</span>
                <h3>{escape(level)} · {escape(category)}</h3>
                <p>{escape(message)}</p>
            </article>
            """
        )
    return "".join(items)


def render_html(report: ReportData) -> str:
    directions = "\n".join(_render_direction(direction) for direction in report.directions)
    products = "\n".join(_render_product(card) for card in report.watchlist)
    alerts = _render_alerts(report.alerts)
    drawdown = _pct(report.risk_metrics.get("current_drawdown"))
    max_drawdown = _pct(report.risk_metrics.get("max_drawdown"))
    win_rate = _pct(report.risk_metrics.get("win_rate"))
    profit_factor = _fmt_number(report.risk_metrics.get("profit_factor"), 2)
    equity = _money(report.account.get("equity"))

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape(report.product_name)} - {escape(report.date)}</title>
    <style>
        :root {{
            --ink: #1f2933;
            --muted: #667085;
            --line: #dce5de;
            --paper: #fbfcf9;
            --card: #ffffff;
            --green: #16745b;
            --green-soft: #e8f4ef;
            --shadow: 0 18px 42px rgba(25, 48, 39, .08);
        }}
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            background:
                radial-gradient(circle at 6% 2%, rgba(22,116,91,.11), transparent 24rem),
                linear-gradient(180deg, #f7faf6 0%, #f1f5f0 100%);
            color: var(--ink);
            font-family: "Microsoft YaHei", "PingFang SC", "Segoe UI", sans-serif;
            line-height: 1.62;
        }}
        .page {{ max-width: 1460px; margin: 0 auto; padding: 0 8px 34px; }}
        .top-line {{ height: 6px; background: var(--green); border-radius: 0 0 3px 3px; }}
        .hero {{
            background: var(--card);
            border: 1px solid var(--line);
            border-radius: 0 0 10px 10px;
            padding: 34px 34px 40px;
            box-shadow: var(--shadow);
        }}
        .kicker {{ color: #697586; font-weight: 700; margin-bottom: 8px; }}
        h1 {{ margin: 0 0 12px; font-size: clamp(38px, 5vw, 76px); line-height: 1.05; letter-spacing: -2px; }}
        .lead {{ max-width: 1000px; margin: 0; color: #465564; font-size: 20px; font-weight: 650; }}
        .grid {{ display: grid; gap: 16px; }}
        .three {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
        .four {{ grid-template-columns: repeat(4, minmax(0, 1fr)); }}
        .section-head {{ display: flex; justify-content: space-between; gap: 16px; align-items: end; margin: 28px 0 10px; }}
        .section-head h2 {{ margin: 0; font-size: 30px; letter-spacing: -1px; }}
        .hint {{ color: #697586; font-weight: 700; }}
        .card {{
            background: rgba(255,255,255,.92);
            border: 1px solid var(--line);
            border-radius: 9px;
            padding: 22px;
            box-shadow: 0 8px 22px rgba(32, 48, 41, .045);
        }}
        .summary-card h2 {{ margin: 8px 0 8px; font-size: 28px; }}
        .card h3 {{ margin: 0 0 8px; font-size: 25px; line-height: 1.18; }}
        .card p {{ margin: 0 0 16px; color: #4b5b68; font-weight: 620; }}
        .muted {{ color: var(--muted); font-size: 14px; font-weight: 700; }}
        .pills {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }}
        .pill {{
            border: 1px solid var(--line);
            background: #fbfdfb;
            color: #65727c;
            border-radius: 999px;
            padding: 4px 12px;
            font-size: 13px;
            font-weight: 700;
        }}
        .product-card {{ min-height: 260px; }}
        .product-head {{ display: flex; justify-content: space-between; gap: 12px; border-bottom: 1px solid var(--line); padding-bottom: 12px; margin-bottom: 12px; }}
        .rank {{ align-self: start; border: 1px solid #a8d7c7; background: var(--green-soft); color: var(--green); border-radius: 999px; padding: 5px 10px; font-weight: 800; }}
        .metrics {{ display: grid; gap: 8px; margin-top: 10px; }}
        .metrics.two {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
        .metrics div {{ border: 1px solid var(--line); border-radius: 8px; padding: 10px 12px; background: #fcfdfb; }}
        .metrics span {{ display: block; color: #7a8794; font-size: 13px; font-weight: 700; }}
        .metrics strong {{ display: block; font-size: 17px; }}
        .step-card span {{ color: var(--green); font-weight: 900; }}
        .footer {{ border: 1px dashed var(--line); border-radius: 9px; padding: 16px 20px; color: #667085; font-weight: 700; margin-top: 24px; background: rgba(255,255,255,.55); }}
        @media (max-width: 980px) {{ .three, .four {{ grid-template-columns: 1fr; }} .hero {{ padding: 28px 22px; }} .section-head {{ display: block; }} }}
    </style>
</head>
<body>
    <main class="page">
        <div class="top-line"></div>
        <section class="hero">
            <div class="kicker">Hermass {escape(report.product_name)} · {escape(report.universe_name)} · {escape(report.date)}</div>
            <h1>今天先看这几个方向</h1>
            <p class="lead">系统不要求普通人理解复杂模型。你只需要知道：当 MT5 产品在趋势、风险、信号三个层面同时进入同一类强状态时，它值得进入观察清单。这里展示的是“先看谁、为什么看、怎么看”。</p>
        </section>

        <section class="grid three" style="margin-top:18px;">
            <article class="card summary-card">
                <div class="muted">今天产品观察</div>
                <h2>有 {report.watch_count} 个进入观察</h2>
                <p>从 {report.total_products} 个产品中筛出，代表价格、信号或风控状态更靠前。</p>
            </article>
            <article class="card summary-card">
                <div class="muted">更保守口径</div>
                <h2>优先看 {report.priority_count} 个</h2>
                <p>适合时间少的人，先用更短清单做晨间观察。</p>
            </article>
            <article class="card summary-card">
                <div class="muted">今天第一眼</div>
                <h2>{escape(report.focus_text)}</h2>
                <p>先观察方向是否集中，再观察单个产品是否有持续状态。</p>
            </article>
        </section>

        <div class="section-head">
            <h2>三个普通人能看懂的方向</h2>
            <div class="hint">不讲复杂术语，只讲观察主题</div>
        </div>
        <section class="grid three">{directions}</section>

        <div class="section-head">
            <h2>MT5 每日观察清单</h2>
            <div class="hint">按观察排序展示，适合普通人先看少一点</div>
        </div>
        <section class="grid three">{products}</section>

        <div class="section-head">
            <h2>账户与风险状态</h2>
            <div class="hint">只看是否需要降低观察频率或暂停</div>
        </div>
        <section class="grid four">
            <article class="card step-card"><span>1</span><h3>账户净值</h3><p>{equity}</p></article>
            <article class="card step-card"><span>2</span><h3>当前回撤</h3><p>{drawdown}</p></article>
            <article class="card step-card"><span>3</span><h3>最大回撤</h3><p>{max_drawdown}</p></article>
            <article class="card step-card"><span>4</span><h3>胜率 / 盈亏比</h3><p>{win_rate} / {profit_factor}</p></article>
        </section>

        <div class="section-head">
            <h2>普通人的 4 步使用方式</h2>
            <div class="hint">每天 3 分钟够用</div>
        </div>
        <section class="grid four">
            <article class="card step-card"><span>1</span><h3>先看方向</h3><p>今天集中在哪些品种，不要一上来盯单个产品。</p></article>
            <article class="card step-card"><span>2</span><h3>再看清单</h3><p>只看观察清单，减少信息噪声。</p></article>
            <article class="card step-card"><span>3</span><h3>看状态是否延续</h3><p>下一次打开，看它是否仍在清单里。</p></article>
            <article class="card step-card"><span>4</span><h3>不做复杂判断</h3><p>普通人只需要建立观察习惯，不需要读懂底层模型。</p></article>
        </section>

        <div class="section-head">
            <h2>系统提醒</h2>
            <div class="hint">来自 MT5 监控与风控模块</div>
        </div>
        <section class="grid four">{alerts}</section>

        <div class="footer">说明：本页是 MT5 产品普通投资者观察版，只用于学习和研究，不构成任何投资或交易建议。它解决的是“今天先观察什么”，不是“今天应该怎么操作”。生成时间：{escape(report.generated_at)}</div>
    </main>
</body>
</html>
"""


def sample_payload() -> Dict[str, Any]:
    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "product_name": "MT5 普通投资者观察版",
        "universe_name": "外汇 / 贵金属 / 指数",
        "total_products": 18,
        "focus_text": "外汇、贵金属更集中",
        "account": {"equity": 10042.8},
        "risk_metrics": {
            "current_drawdown": 0.012,
            "max_drawdown": 0.047,
            "win_rate": 0.56,
            "profit_factor": 1.38,
        },
        "watchlist": [
            {"symbol": "XAUUSD", "name": "黄金", "theme": "贵金属", "state": "趋势 / 风险 / 信号同向", "price": 2385.42, "spread": 18, "confidence": 0.72, "tags": ["避险资产", "强趋势"], "note": "黄金进入多层观察状态，适合先看避险方向是否延续。"},
            {"symbol": "EURUSD", "name": "欧元兑美元", "theme": "主流外汇", "state": "趋势延续", "price": 1.08752, "spread": 1.2, "confidence": 0.66, "tags": ["主流货币", "BUY"], "note": "主流货币对方向相对清晰，适合作为外汇方向代表。"},
            {"symbol": "USDJPY", "name": "美元兑日元", "theme": "主流外汇", "state": "高波动观察", "price": 156.214, "spread": 1.6, "confidence": 0.61, "tags": ["日元", "高波动"], "note": "波动放大，普通人只观察状态是否持续，不急于判断。"},
            {"symbol": "NAS100", "name": "纳指100", "theme": "股指", "state": "动量观察", "price": 18642.2, "spread": 2.5, "confidence": 0.59, "tags": ["科技股指"], "note": "股指方向样本，适合和 US500 一起看风险偏好。"},
            {"symbol": "GBPUSD", "name": "英镑兑美元", "theme": "主流外汇", "state": "等待确认", "price": 1.27311, "spread": 1.5, "confidence": 0.55, "tags": ["主流货币"], "note": "信号尚未完全统一，适合放在后续观察位。"},
            {"symbol": "WTI", "name": "原油", "theme": "能源", "state": "事件后观察", "price": 79.48, "spread": 4.0, "confidence": 0.58, "tags": ["能源", "高波动"], "note": "能源波动通常更大，普通人只看方向持续性。"},
        ],
        "alerts": [
            {"level": "INFO", "category": "SYSTEM", "message": "MT5 连接状态正常，今日报告可按观察清单使用。"}
        ],
    }


def write_report(input_path: Optional[Path], output_path: Optional[Path]) -> Path:
    payload = _load_json(input_path)
    report = _normalize_payload(payload)
    html = render_html(report)

    if output_path is None:
        DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = DEFAULT_OUTPUT_DIR / f"mt5_daily_report_{report.date.replace('-', '')}.html"
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(html, encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate MT5 daily observer HTML report.")
    parser.add_argument("--input", type=Path, help="JSON snapshot path. Uses sample data if omitted.")
    parser.add_argument("--output", type=Path, help="Output HTML path.")
    args = parser.parse_args()

    output_path = write_report(args.input, args.output)
    print(f"MT5 daily report generated: {output_path}")


if __name__ == "__main__":
    main()

