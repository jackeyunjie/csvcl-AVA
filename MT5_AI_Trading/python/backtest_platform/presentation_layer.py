"""
展示层 (Presentation Layer)

职责: 将回测结果转换为可视化报告。

模块:
- HTMLReportGenerator: HTML报告生成器（Jinja2模板）
- PlotlyChartBuilder: Plotly交互式图表构建器
- ReportExporter: 多格式导出器（HTML/JSON/SQX）

核心原则:
- 一键生成完整回测报告
- 交互式图表支持缩放/筛选
- State-Regime可视化：按状态组合展示绩效
- 移动端友好响应式布局
"""

import os
import sys
import json
import base64
import logging
from typing import Dict, List, Optional, Any
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import pandas as pd
import numpy as np

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest_platform.execution_layer import PerformanceReport, Trade, DailyStats

logger = logging.getLogger(__name__)

# ============================================================================
# Plotly 图表构建器
# ============================================================================

class PlotlyChartBuilder:
    """
    Plotly交互式图表构建器

    生成以下图表:
    1. 净值曲线 (Equity Curve)
    2. 回撤曲线 (Drawdown)
    3. 月度收益热力图 (Monthly Returns Heatmap)
    4. 交易分布 (Trade Distribution)
    5. State-Regime绩效对比 (State Regime Performance)
    6. 盈亏散点图 (P&L Scatter)
    """

    def __init__(self):
        self.charts: Dict[str, str] = {}

    def _check_plotly(self) -> bool:
        """检查plotly是否可用"""
        try:
            import plotly.graph_objects as go
            import plotly.express as px
            from plotly.subplots import make_subplots
            return True
        except ImportError:
            logger.warning("plotly未安装，图表功能不可用。请运行: pip install plotly")
            return False

    def build_all_charts(self, report: PerformanceReport) -> Dict[str, str]:
        """
        构建所有图表，返回 {chart_name: html_div} 字典
        """
        if not self._check_plotly():
            return {}

        self.charts = {}

        # 准备数据
        daily_df = self._daily_stats_to_df(report.daily_stats)
        trades_df = self._trades_to_df(report.trades)

        # 1. 净值曲线 + 回撤
        self.charts['equity_drawdown'] = self._build_equity_drawdown_chart(daily_df)

        # 2. 月度收益热力图
        self.charts['monthly_heatmap'] = self._build_monthly_heatmap(daily_df)

        # 3. 交易分布
        if not trades_df.empty:
            self.charts['trade_distribution'] = self._build_trade_distribution(trades_df)
            self.charts['pnl_scatter'] = self._build_pnl_scatter(trades_df)

        # 4. State-Regime绩效
        if report.state_regime_stats:
            self.charts['state_regime'] = self._build_state_regime_chart(report.state_regime_stats)

        # 5. 交易时间线
        if not trades_df.empty:
            self.charts['trade_timeline'] = self._build_trade_timeline(trades_df, daily_df)

        return self.charts

    def _daily_stats_to_df(self, daily_stats: List[DailyStats]) -> pd.DataFrame:
        """每日统计转DataFrame"""
        if not daily_stats:
            return pd.DataFrame()
        data = []
        for ds in daily_stats:
            data.append({
                'date': ds.date,
                'balance': ds.balance,
                'equity': ds.equity,
                'daily_pnl': ds.daily_pnl,
                'daily_return_pct': ds.daily_return_pct,
                'drawdown_pct': ds.drawdown_pct,
                'high_water_mark': ds.high_water_mark,
                'open_positions': ds.open_positions,
            })
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        return df

    def _trades_to_df(self, trades: List[Trade]) -> pd.DataFrame:
        """交易记录转DataFrame"""
        if not trades:
            return pd.DataFrame()
        data = []
        for t in trades:
            data.append({
                'entry_time': t.entry_time,
                'exit_time': t.exit_time,
                'direction': t.direction,
                'entry_price': t.entry_price,
                'exit_price': t.exit_price,
                'pnl': t.pnl,
                'pnl_pct': t.pnl_pct,
                'holding_bars': t.holding_bars,
                'exit_reason': t.exit_reason,
                'entry_triplet': str(t.entry_triplet) if t.entry_triplet else None,
            })
        df = pd.DataFrame(data)
        df['entry_time'] = pd.to_datetime(df['entry_time'])
        df['exit_time'] = pd.to_datetime(df['exit_time'])
        return df

    def _build_equity_drawdown_chart(self, df: pd.DataFrame) -> str:
        """净值曲线 + 回撤子图"""
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        if df.empty:
            return ""

        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            row_heights=[0.7, 0.3],
            subplot_titles=('净值曲线', '回撤 %')
        )

        # 净值曲线
        fig.add_trace(
            go.Scatter(
                x=df['date'], y=df['equity'],
                mode='lines', name='净值',
                line=dict(color='#2196F3', width=1.5),
                fill='tozeroy', fillcolor='rgba(33,150,243,0.1)',
            ),
            row=1, col=1
        )

        # 水位线
        fig.add_trace(
            go.Scatter(
                x=df['date'], y=df['high_water_mark'],
                mode='lines', name='最高水位',
                line=dict(color='#4CAF50', width=1, dash='dash'),
            ),
            row=1, col=1
        )

        # 回撤
        fig.add_trace(
            go.Scatter(
                x=df['date'], y=df['drawdown_pct'],
                mode='lines', name='回撤',
                line=dict(color='#F44336', width=1),
                fill='tozeroy', fillcolor='rgba(244,67,54,0.15)',
            ),
            row=2, col=1
        )

        fig.update_layout(
            height=500,
            showlegend=True,
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
            margin=dict(l=50, r=50, t=80, b=50),
            hovermode='x unified',
            template='plotly_white',
        )

        fig.update_yaxes(title_text='资金', row=1, col=1)
        fig.update_yaxes(title_text='回撤 %', row=2, col=1)
        fig.update_xaxes(title_text='日期', row=2, col=1)

        return fig.to_html(full_html=False, include_plotlyjs='cdn')

    def _build_monthly_heatmap(self, df: pd.DataFrame) -> str:
        """月度收益热力图"""
        import plotly.graph_objects as go

        if df.empty or len(df) < 20:
            return ""

        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        monthly = df.groupby(['year', 'month'])['daily_return_pct'].sum().reset_index()
        monthly['month_str'] = monthly['month'].apply(lambda m: f'{m:02d}')

        # 构建透视表
        pivot = monthly.pivot(index='year', columns='month', values='daily_return_pct')
        pivot = pivot.reindex(columns=range(1, 13))

        fig = go.Figure(data=go.Heatmap(
            z=pivot.values,
            x=[f'{m}月' for m in range(1, 13)],
            y=[str(y) for y in pivot.index],
            colorscale=[
                [0, '#F44336'],
                [0.5, '#FFFFFF'],
                [1, '#4CAF50'],
            ],
            zmid=0,
            text=[[f'{v:.2f}%' if pd.notna(v) else '' for v in row] for row in pivot.values],
            texttemplate='%{text}',
            textfont={'size': 10},
            hovertemplate='%{y}年 %{x}: %{z:.2f}%<extra></extra>',
        ))

        fig.update_layout(
            title='月度收益热力图 (%)',
            height=300,
            margin=dict(l=50, r=50, t=50, b=50),
            template='plotly_white',
        )

        return fig.to_html(full_html=False, include_plotlyjs='cdn')

    def _build_trade_distribution(self, df: pd.DataFrame) -> str:
        """交易分布图（盈亏直方图 + 方向饼图）"""
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        fig = make_subplots(
            rows=1, cols=2,
            specs=[[{"type": "histogram"}, {"type": "pie"}]],
            subplot_titles=('盈亏分布', '多空分布')
        )

        # 盈亏直方图
        colors = ['#4CAF50' if p >= 0 else '#F44336' for p in df['pnl']]
        fig.add_trace(
            go.Histogram(
                x=df['pnl'],
                nbinsx=20,
                marker_color=colors,
                name='盈亏',
                showlegend=False,
            ),
            row=1, col=1
        )

        # 多空饼图
        long_count = (df['direction'] == 'long').sum()
        short_count = (df['direction'] == 'short').sum()
        fig.add_trace(
            go.Pie(
                labels=['多单', '空单'],
                values=[long_count, short_count],
                marker_colors=['#2196F3', '#FF9800'],
                textinfo='label+percent',
                showlegend=False,
            ),
            row=1, col=2
        )

        fig.update_layout(
            height=350,
            margin=dict(l=50, r=50, t=50, b=50),
            template='plotly_white',
        )

        return fig.to_html(full_html=False, include_plotlyjs='cdn')

    def _build_pnl_scatter(self, df: pd.DataFrame) -> str:
        """盈亏散点图（持仓时间 vs 盈亏）"""
        import plotly.graph_objects as go

        fig = go.Figure()

        # 盈利交易
        wins = df[df['pnl'] >= 0]
        fig.add_trace(go.Scatter(
            x=wins['holding_bars'],
            y=wins['pnl'],
            mode='markers',
            name='盈利',
            marker=dict(color='#4CAF50', size=10, opacity=0.7),
            text=[f'入场: {t}<br>盈亏: {p:+.2f}' for t, p in zip(wins['entry_time'], wins['pnl'])],
            hovertemplate='%{text}<extra></extra>',
        ))

        # 亏损交易
        losses = df[df['pnl'] < 0]
        fig.add_trace(go.Scatter(
            x=losses['holding_bars'],
            y=losses['pnl'],
            mode='markers',
            name='亏损',
            marker=dict(color='#F44336', size=10, opacity=0.7),
            text=[f'入场: {t}<br>盈亏: {p:+.2f}' for t, p in zip(losses['entry_time'], losses['pnl'])],
            hovertemplate='%{text}<extra></extra>',
        ))

        fig.update_layout(
            title='盈亏 vs 持仓时间',
            xaxis_title='持仓K线数',
            yaxis_title='盈亏',
            height=400,
            margin=dict(l=50, r=50, t=50, b=50),
            template='plotly_white',
            hovermode='closest',
        )

        return fig.to_html(full_html=False, include_plotlyjs='cdn')

    def _build_state_regime_chart(self, state_regime_stats: Dict) -> str:
        """State-Regime绩效对比图"""
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        regimes = list(state_regime_stats.keys())
        win_rates = [state_regime_stats[r].win_rate * 100 for r in regimes]
        total_pnls = [state_regime_stats[r].total_pnl for r in regimes]
        trade_counts = [state_regime_stats[r].total_trades for r in regimes]

        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('胜率 %', '总盈亏'),
        )

        colors_wr = ['#4CAF50' if w >= 50 else '#F44336' for w in win_rates]
        fig.add_trace(
            go.Bar(
                x=regimes, y=win_rates,
                marker_color=colors_wr,
                text=[f'{w:.1f}%' for w in win_rates],
                textposition='auto',
                showlegend=False,
            ),
            row=1, col=1
        )

        colors_pnl = ['#4CAF50' if p >= 0 else '#F44336' for p in total_pnls]
        fig.add_trace(
            go.Bar(
                x=regimes, y=total_pnls,
                marker_color=colors_pnl,
                text=[f'{p:+.2f}' for p in total_pnls],
                textposition='auto',
                showlegend=False,
            ),
            row=1, col=2
        )

        fig.update_layout(
            height=350,
            margin=dict(l=50, r=50, t=50, b=80),
            template='plotly_white',
        )

        return fig.to_html(full_html=False, include_plotlyjs='cdn')

    def _build_trade_timeline(self, trades_df: pd.DataFrame, daily_df: pd.DataFrame) -> str:
        """交易时间线（在净值曲线上标注入场/出场点）"""
        import plotly.graph_objects as go

        fig = go.Figure()

        # 净值曲线
        fig.add_trace(go.Scatter(
            x=daily_df['date'], y=daily_df['equity'],
            mode='lines', name='净值',
            line=dict(color='#2196F3', width=1.5),
        ))

        # 入场点
        for _, trade in trades_df.iterrows():
            color = '#4CAF50' if trade['pnl'] >= 0 else '#F44336'
            symbol = 'triangle-up' if trade['direction'] == 'long' else 'triangle-down'

            # 找到入场日对应的净值
            entry_date = trade['entry_time']
            equity_on_entry = daily_df[daily_df['date'] <= entry_date]['equity'].iloc[-1] if not daily_df.empty else trade['entry_price']

            fig.add_trace(go.Scatter(
                x=[entry_date],
                y=[equity_on_entry],
                mode='markers',
                marker=dict(color=color, symbol=symbol, size=12),
                showlegend=False,
                hovertemplate=f"方向: {trade['direction']}<br>盈亏: {trade['pnl']:+.2f}<br>原因: {trade['exit_reason']}<extra></extra>",
            ))

        fig.update_layout(
            title='交易时间线（▲多单 ▼空单，绿色盈利 红色亏损）',
            xaxis_title='日期',
            yaxis_title='净值',
            height=400,
            margin=dict(l=50, r=50, t=50, b=50),
            template='plotly_white',
            hovermode='closest',
        )

        return fig.to_html(full_html=False, include_plotlyjs='cdn')


# ============================================================================
# HTML 报告生成器
# ============================================================================

class HTMLReportGenerator:
    """
    HTML报告生成器

    使用Jinja2模板引擎生成完整的回测报告HTML文件。
    包含：
    - 绩效概览卡片
    - Plotly交互式图表
    - 交易明细表格
    - State-Regime分析
    - 系统信息
    """

    def __init__(self, output_dir: str = "reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.chart_builder = PlotlyChartBuilder()

    def generate(self, report: PerformanceReport, strategy_name: str = "") -> str:
        """
        生成HTML报告

        Args:
            report: 绩效报告
            strategy_name: 策略名称

        Returns:
            生成的HTML文件路径
        """
        # 构建图表
        charts = self.chart_builder.build_all_charts(report)

        # 准备模板数据
        template_data = self._prepare_template_data(report, strategy_name, charts)

        # 渲染HTML
        html_content = self._render_html(template_data)

        # 保存文件
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"backtest_report_{report.symbol}_{timestamp}.html"
        filepath = self.output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)

        logger.info(f"HTML报告已生成: {filepath}")
        return str(filepath)

    def _prepare_template_data(self, report: PerformanceReport, strategy_name: str, charts: Dict[str, str]) -> Dict[str, Any]:
        """准备模板数据"""
        # 交易明细
        trades_data = []
        for t in report.trades:
            trades_data.append({
                'entry_time': t.entry_time.strftime('%Y-%m-%d') if hasattr(t.entry_time, 'strftime') else str(t.entry_time)[:10],
                'exit_time': t.exit_time.strftime('%Y-%m-%d') if hasattr(t.exit_time, 'strftime') else str(t.exit_time)[:10],
                'direction': '多' if t.direction == 'long' else '空',
                'entry_price': f"{t.entry_price:.5f}",
                'exit_price': f"{t.exit_price:.5f}",
                'pnl': f"{t.pnl:+.2f}",
                'pnl_pct': f"{t.pnl_pct:+.2f}%",
                'holding_bars': t.holding_bars,
                'exit_reason': self._translate_exit_reason(t.exit_reason),
                'entry_triplet': str(t.entry_triplet) if t.entry_triplet else '-',
            })

        # State-Regime数据
        regime_data = []
        for regime_id, stats in sorted(report.state_regime_stats.items()):
            regime_data.append({
                'regime_id': regime_id,
                'total_trades': stats.total_trades,
                'win_rate': f"{stats.win_rate:.1%}",
                'total_pnl': f"{stats.total_pnl:+.2f}",
                'avg_pnl': f"{stats.avg_pnl:+.2f}",
                'profit_factor': f"{stats.profit_factor:.2f}",
            })

        return {
            'report': report,
            'strategy_name': strategy_name or 'P107 State Hex Strategy',
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'charts': charts,
            'trades': trades_data,
            'regimes': regime_data,
            'summary': {
                'total_return_pct': f"{report.total_return_pct:+.2f}%",
                'total_trades': report.total_trades,
                'win_rate': f"{report.win_rate:.1%}",
                'profit_factor': f"{report.profit_factor:.2f}",
                'max_drawdown_pct': f"{report.max_drawdown_pct:.2f}%",
                'sharpe_ratio': f"{report.sharpe_ratio:.2f}",
                'sortino_ratio': f"{report.sortino_ratio:.2f}",
                'calmar_ratio': f"{report.calmar_ratio:.2f}",
                'avg_profit': f"{report.avg_profit:+.2f}",
                'avg_loss': f"{report.avg_loss:+.2f}",
                'expectancy': f"{report.expectancy:+.2f}",
                'initial_balance': f"{report.initial_balance:,.2f}",
                'final_balance': f"{report.final_balance:,.2f}",
                'start_date': report.start_date.strftime('%Y-%m-%d') if hasattr(report.start_date, 'strftime') else str(report.start_date)[:10],
                'end_date': report.end_date.strftime('%Y-%m-%d') if hasattr(report.end_date, 'strftime') else str(report.end_date)[:10],
            },
        }

    def _translate_exit_reason(self, reason: str) -> str:
        """翻译退出原因"""
        mapping = {
            'sl': '止损',
            'tp': '止盈',
            'signal_flip': '信号翻转',
            'end_of_data': '数据结束',
            'manual': '手动平仓',
        }
        return mapping.get(reason, reason)

    def _render_html(self, data: Dict[str, Any]) -> str:
        """渲染HTML模板"""
        # 使用内联模板，避免外部文件依赖
        template = self._get_html_template()

        # 简单模板替换（不使用Jinja2，减少依赖）
        html = template

        # 替换基本字段
        for key, value in data['summary'].items():
            html = html.replace(f'{{{{{key}}}}}', str(value))

        html = html.replace('{{strategy_name}}', data['strategy_name'])
        html = html.replace('{{generated_at}}', data['generated_at'])

        # 插入图表
        for chart_name, chart_html in data['charts'].items():
            placeholder = f'{{{{chart_{chart_name}}}}}'
            html = html.replace(placeholder, chart_html or '<p style="color:#999;text-align:center;padding:40px;">图表数据不足</p>')

        # 交易明细表格
        trades_rows = ''
        for t in data['trades']:
            pnl_color = 'color:#4CAF50;' if float(t['pnl'].replace('+', '').replace(',', '')) >= 0 else 'color:#F44336;'
            trades_rows += f"""
            <tr>
                <td>{t['entry_time']}</td>
                <td>{t['exit_time']}</td>
                <td>{t['direction']}</td>
                <td>{t['entry_price']}</td>
                <td>{t['exit_price']}</td>
                <td style="{pnl_color}font-weight:600;">{t['pnl']}</td>
                <td style="{pnl_color}">{t['pnl_pct']}</td>
                <td>{t['holding_bars']}</td>
                <td>{t['exit_reason']}</td>
                <td><code>{t['entry_triplet']}</code></td>
            </tr>
            """
        html = html.replace('{{trades_rows}}', trades_rows or '<tr><td colspan="10" style="text-align:center;color:#999;">无交易记录</td></tr>')

        # State-Regime表格
        regime_rows = ''
        for r in data['regimes']:
            pnl_color = 'color:#4CAF50;' if float(r['total_pnl'].replace('+', '').replace(',', '')) >= 0 else 'color:#F44336;'
            regime_rows += f"""
            <tr>
                <td><code>{r['regime_id']}</code></td>
                <td>{r['total_trades']}</td>
                <td>{r['win_rate']}</td>
                <td style="{pnl_color}font-weight:600;">{r['total_pnl']}</td>
                <td>{r['avg_pnl']}</td>
                <td>{r['profit_factor']}</td>
            </tr>
            """
        html = html.replace('{{regime_rows}}', regime_rows or '<tr><td colspan="6" style="text-align:center;color:#999;">无State-Regime数据</td></tr>')

        return html

    def _get_html_template(self) -> str:
        """获取HTML模板"""
        return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>State Hex 回测报告 - {{strategy_name}}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f5f7fa;
            color: #333;
            line-height: 1.6;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 24px;
        }
        .header h1 { font-size: 24px; margin-bottom: 8px; }
        .header .meta { opacity: 0.9; font-size: 14px; }
        .cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        .card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }
        .card .label {
            font-size: 12px;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }
        .card .value {
            font-size: 22px;
            font-weight: 700;
        }
        .card .value.positive { color: #4CAF50; }
        .card .value.negative { color: #F44336; }
        .section {
            background: white;
            padding: 24px;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            margin-bottom: 24px;
        }
        .section h2 {
            font-size: 18px;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 2px solid #f0f0f0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }
        th, td {
            padding: 10px 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        th {
            background: #f8f9fa;
            font-weight: 600;
            color: #555;
            font-size: 12px;
            text-transform: uppercase;
        }
        tr:hover { background: #f8f9fa; }
        code {
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 12px;
            font-family: 'Courier New', monospace;
        }
        .footer {
            text-align: center;
            color: #999;
            font-size: 12px;
            padding: 20px;
        }
        @media (max-width: 768px) {
            .cards { grid-template-columns: 1fr 1fr; }
            .container { padding: 10px; }
            .header { padding: 20px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>State Hex 自主回测平台 - 绩效报告</h1>
            <div class="meta">
                策略: {{strategy_name}} | 品种: {{symbol}} |
                区间: {{start_date}} ~ {{end_date}} |
                生成时间: {{generated_at}}
            </div>
        </div>

        <div class="cards">
            <div class="card">
                <div class="label">总收益率</div>
                <div class="value {{ 'positive' if total_return_pct.startswith('+') else 'negative' }}">{{total_return_pct}}</div>
            </div>
            <div class="card">
                <div class="label">总交易数</div>
                <div class="value">{{total_trades}}</div>
            </div>
            <div class="card">
                <div class="label">胜率</div>
                <div class="value">{{win_rate}}</div>
            </div>
            <div class="card">
                <div class="label">盈亏比</div>
                <div class="value">{{profit_factor}}</div>
            </div>
            <div class="card">
                <div class="label">最大回撤</div>
                <div class="value negative">{{max_drawdown_pct}}</div>
            </div>
            <div class="card">
                <div class="label">夏普比率</div>
                <div class="value">{{sharpe_ratio}}</div>
            </div>
            <div class="card">
                <div class="label">Sortino</div>
                <div class="value">{{sortino_ratio}}</div>
            </div>
            <div class="card">
                <div class="label">Calmar</div>
                <div class="value">{{calmar_ratio}}</div>
            </div>
        </div>

        <div class="section">
            <h2>净值曲线 & 回撤</h2>
            {{chart_equity_drawdown}}
        </div>

        <div class="section">
            <h2>月度收益热力图</h2>
            {{chart_monthly_heatmap}}
        </div>

        <div class="section">
            <h2>交易分布</h2>
            {{chart_trade_distribution}}
        </div>

        <div class="section">
            <h2>盈亏散点图</h2>
            {{chart_pnl_scatter}}
        </div>

        <div class="section">
            <h2>交易时间线</h2>
            {{chart_trade_timeline}}
        </div>

        <div class="section">
            <h2>State-Regime 绩效分析</h2>
            {{chart_state_regime}}
            <table style="margin-top:16px;">
                <thead>
                    <tr>
                        <th>状态组合</th>
                        <th>交易数</th>
                        <th>胜率</th>
                        <th>总盈亏</th>
                        <th>平均盈亏</th>
                        <th>盈亏比</th>
                    </tr>
                </thead>
                <tbody>
                    {{regime_rows}}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>交易明细</h2>
            <div style="overflow-x:auto;">
                <table>
                    <thead>
                        <tr>
                            <th>入场日期</th>
                            <th>出场日期</th>
                            <th>方向</th>
                            <th>入场价</th>
                            <th>出场价</th>
                            <th>盈亏</th>
                            <th>盈亏%</th>
                            <th>持仓K线</th>
                            <th>退出原因</th>
                            <th>入场三元组</th>
                        </tr>
                    </thead>
                    <tbody>
                        {{trades_rows}}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="footer">
            <p>State Hex 自主回测平台 | 基于 P107 State Hex + P106 Moneyflow 引擎</p>
            <p>生成时间: {{generated_at}}</p>
        </div>
    </div>
</body>
</html>"""


# ============================================================================
# 报告导出器
# ============================================================================

class ReportExporter:
    """
    报告多格式导出器

    支持格式:
    - HTML (完整交互式报告)
    - JSON (结构化数据)
    - SQX (StrategyQuant X 兼容)
    - CSV (交易明细)
    """

    def __init__(self, output_dir: str = "reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.html_generator = HTMLReportGenerator(output_dir)

    def export_all(self, report: PerformanceReport, strategy_name: str = "") -> Dict[str, str]:
        """
        导出所有格式

        Returns:
            {format: filepath}
        """
        results = {}
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_name = f"{report.symbol}_{timestamp}"

        # HTML
        try:
            html_path = self.html_generator.generate(report, strategy_name)
            results['html'] = html_path
        except Exception as e:
            logger.error(f"HTML导出失败: {e}")

        # JSON
        try:
            json_path = self._export_json(report, base_name)
            results['json'] = json_path
        except Exception as e:
            logger.error(f"JSON导出失败: {e}")

        # CSV (交易明细)
        try:
            csv_path = self._export_csv(report, base_name)
            results['csv'] = csv_path
        except Exception as e:
            logger.error(f"CSV导出失败: {e}")

        # SQX
        try:
            sqx_path = self._export_sqx(report, base_name)
            results['sqx'] = sqx_path
        except Exception as e:
            logger.error(f"SQX导出失败: {e}")

        return results

    def _export_json(self, report: PerformanceReport, base_name: str) -> str:
        """导出JSON"""
        from backtest_platform.execution_layer import ReportPrinter
        data = ReportPrinter.to_dict(report)

        filepath = self.output_dir / f"{base_name}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return str(filepath)

    def _export_csv(self, report: PerformanceReport, base_name: str) -> str:
        """导出交易明细CSV"""
        if not report.trades:
            return ""

        data = []
        for t in report.trades:
            data.append({
                'entry_time': t.entry_time,
                'exit_time': t.exit_time,
                'direction': t.direction,
                'entry_price': t.entry_price,
                'exit_price': t.exit_price,
                'pnl': t.pnl,
                'pnl_pct': t.pnl_pct,
                'holding_bars': t.holding_bars,
                'exit_reason': t.exit_reason,
            })

        df = pd.DataFrame(data)
        filepath = self.output_dir / f"{base_name}_trades.csv"
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        return str(filepath)

    def _export_sqx(self, report: PerformanceReport, base_name: str) -> str:
        """导出SQX格式"""
        from backtest_platform.execution_layer import ReportPrinter
        data = ReportPrinter.export_sqx(report)

        filepath = self.output_dir / f"{base_name}_sqx.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return str(filepath)


# ============================================================================
# 测试入口
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("展示层测试")
    print("=" * 70)

    # 创建模拟报告
    from backtest_platform.execution_layer import PerformanceReport, Trade, DailyStats, StateRegimeMetrics
    from ai_engine.state_hex_engine import StateHexTriplet

    # 模拟交易
    trades = [
        Trade(
            symbol="EURUSD", direction="long",
            entry_time=datetime(2024, 1, 15), exit_time=datetime(2024, 1, 20),
            entry_price=1.0850, exit_price=1.0920,
            volume=0.1, pnl=70.0, pnl_pct=0.65,
            commission=5.0, slippage=0.5, holding_bars=5,
            exit_reason="tp",
        ),
        Trade(
            symbol="EURUSD", direction="short",
            entry_time=datetime(2024, 2, 1), exit_time=datetime(2024, 2, 5),
            entry_price=1.0920, exit_price=1.0880,
            volume=0.1, pnl=40.0, pnl_pct=0.37,
            commission=5.0, slippage=0.5, holding_bars=4,
            exit_reason="signal_flip",
        ),
    ]

    # 模拟每日统计
    daily_stats = []
    for i in range(60):
        date = datetime(2024, 1, 1) + pd.Timedelta(days=i)
        equity = 10000 + i * 15 + np.sin(i * 0.2) * 200
        hwm = max(10000 + j * 15 + np.sin(j * 0.2) * 200 for j in range(i + 1))
        dd = (hwm - equity) / hwm * 100
        daily_stats.append(DailyStats(
            date=date,
            balance=equity,
            equity=equity,
            unrealized_pnl=0,
            open_positions=0,
            daily_pnl=15 + np.sin(i * 0.2) * 10,
            daily_return_pct=0.15,
            high_water_mark=hwm,
            drawdown_pct=dd,
        ))

    # State-Regime
    regime_stats = {
        "W1:8|MN1:8": StateRegimeMetrics(
            regime_id="W1:8|MN1:8",
            total_trades=2, winning_trades=2, losing_trades=0,
            win_rate=1.0, total_pnl=110.0, avg_pnl=55.0,
            avg_profit=55.0, avg_loss=0.0, profit_factor=999.99,
            max_consecutive_wins=2, max_consecutive_losses=0,
        )
    }

    report = PerformanceReport(
        symbol="EURUSD",
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 3, 1),
        initial_balance=10000.0,
        final_balance=10110.0,
        total_return_pct=1.1,
        total_trades=2,
        winning_trades=2,
        losing_trades=0,
        win_rate=1.0,
        avg_profit=55.0,
        avg_loss=0.0,
        profit_factor=999.99,
        max_drawdown_pct=2.5,
        max_drawdown_duration=5,
        sharpe_ratio=1.85,
        sortino_ratio=2.1,
        calmar_ratio=0.44,
        expectancy=55.0,
        avg_trade_return=55.0,
        state_regime_stats=regime_stats,
        trades=trades,
        daily_stats=daily_stats,
    )

    # 测试HTML生成
    print("\n[1] 测试HTML报告生成...")
    generator = HTMLReportGenerator(output_dir="test_reports")
    html_path = generator.generate(report, strategy_name="P107_StateHex_v1")
    print(f"  HTML报告: {html_path}")

    # 测试多格式导出
    print("\n[2] 测试多格式导出...")
    exporter = ReportExporter(output_dir="test_reports")
    paths = exporter.export_all(report, strategy_name="P107_StateHex_v1")
    for fmt, path in paths.items():
        print(f"  {fmt.upper()}: {path}")

    print("\n" + "=" * 70)
    print("展示层测试完成")
    print("=" * 70)
