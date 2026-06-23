#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为飞书文档生成图表 PNG 图片
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 雷达图维度
dimensions = [
    "趋势强度",
    "RSIOMA动量",
    "SR结构",
    "多周期共振",
    "波动率收缩",
    "反转确认",
    "风险可控性",
]

current = [6, 7, 8, 7, 8, 7, 6]
ideal = [8, 9, 9, 9, 8, 9, 8]
weak = [4, 4, 5, 4, 5, 3, 4]

radar_fig = go.Figure()
radar_fig.add_trace(go.Scatterpolar(
    r=current + [current[0]],
    theta=dimensions + [dimensions[0]],
    fill='toself',
    name='当前 XAUUSD 观测',
    line_color='#00BCD4',
    fillcolor='rgba(0, 188, 212, 0.25)',
))
radar_fig.add_trace(go.Scatterpolar(
    r=ideal + [ideal[0]],
    theta=dimensions + [dimensions[0]],
    fill='toself',
    name='理想反转突破场景',
    line_color='#4CAF50',
    fillcolor='rgba(76, 175, 80, 0.15)',
))
radar_fig.add_trace(go.Scatterpolar(
    r=weak + [weak[0]],
    theta=dimensions + [dimensions[0]],
    fill='toself',
    name='弱势/假突破警戒',
    line_color='#F44336',
    fillcolor='rgba(244, 67, 54, 0.15)',
))
radar_fig.update_layout(
    polar=dict(
        radialaxis=dict(visible=True, range=[0, 10]),
        angularaxis=dict(direction="clockwise"),
    ),
    showlegend=True,
    title=dict(text="XAUUSD 多时间框架技术面观测雷达图", x=0.5, font=dict(size=18)),
    legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
    height=600,
    template="plotly_white",
)
radar_fig.write_image("reports/radar_chart.png", scale=2)

# 因子图
factors = [
    {"name": "H4 SR 下沿支撑有效", "score": 8},
    {"name": "H1 SR 带收缩", "score": 7},
    {"name": "1日/3日枢轴收敛", "score": 6},
    {"name": "RSIOMA 低位金叉", "score": 8},
    {"name": "ADX 趋势强度配合", "score": 5},
    {"name": "假跌破后快速收回", "score": 7},
    {"name": "上方 H4 阻力仍存", "score": -4},
    {"name": "宏观事件不确定性", "score": -3},
]
factor_names = [f["name"] for f in factors]
factor_scores = [f["score"] for f in factors]
factor_colors = ['#4CAF50' if s > 0 else '#F44336' for s in factor_scores]

factor_fig = go.Figure()
factor_fig.add_trace(go.Bar(
    y=factor_names,
    x=factor_scores,
    orientation='h',
    marker_color=factor_colors,
    text=[f"{s:+.0f}" for s in factor_scores],
    textposition='outside',
))
factor_fig.update_layout(
    title=dict(text="反转突破因子贡献图", x=0.5, font=dict(size=18)),
    xaxis=dict(title="因子得分（+ 利多 / - 利空）", range=[-10, 10]),
    yaxis=dict(title=""),
    height=500,
    template="plotly_white",
    margin=dict(l=180),
)
factor_fig.write_image("reports/factor_chart.png", scale=2)

# 热力图
timeframe_data = {
    "时间框架": ["M15", "M30", "H1", "H4"],
    "SR 收缩度": [8, 7, 6, 5],
    "反转信号强度": [7, 8, 6, 5],
    "可信度": [6, 7, 7, 6],
}
heatmap_fig = go.Figure(data=go.Heatmap(
    z=[timeframe_data["SR 收缩度"], timeframe_data["反转信号强度"], timeframe_data["可信度"]],
    x=timeframe_data["时间框架"],
    y=["SR 收缩度", "反转信号强度", "可信度"],
    colorscale="RdYlGn",
    zmin=0,
    zmax=10,
    text=[timeframe_data["SR 收缩度"], timeframe_data["反转信号强度"], timeframe_data["可信度"]],
    texttemplate="%{text}",
    textfont={"size": 14},
))
heatmap_fig.update_layout(
    title=dict(text="多时间框架评分热力图", x=0.5, font=dict(size=18)),
    height=350,
    template="plotly_white",
)
heatmap_fig.write_image("reports/heatmap_chart.png", scale=2)

print("图片已生成：")
print("  reports/radar_chart.png")
print("  reports/factor_chart.png")
print("  reports/heatmap_chart.png")
