#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI交易平台 — 一键启动脚本 (Windows PowerShell)

功能：自动激活虚拟环境 → 测试连接 → 进入交互菜单

用法：在 d:\qoder\csvcl - AVA\MT5_AI_Trading 目录下
      右键 → 用PowerShell运行此脚本
"""

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "   AI 交易平台 — 启动器 v2.0" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# 检查Python
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "[错误] 未找到Python" -ForegroundColor Red
    pause; exit 1
}
Write-Host "[Python] $($py.Version)" -ForegroundColor Green

# 激活虚拟环境
if (Test-Path ".venv\Scripts\Activate.ps1") {
    . .venv\Scripts\Activate.ps1
    Write-Host "[环境] 虚拟环境已激活" -ForegroundColor Green
}

Write-Host ""
Write-Host "请选择操作:" -ForegroundColor Yellow
Write-Host "  1 - 连接测试（检查MT5是否在线）"
Write-Host "  2 - 模拟下单测试（0.01手EURUSD开仓+平仓）"
Write-Host "  3 - 启动AI策略引擎（DryRun模拟模式，持续运行）"
Write-Host "  4 - 启动AI策略引擎（实盘Live模式！！！）"
Write-Host "  q - 退出"
Write-Host ""

$choice = Read-Host "输入数字"

switch ($choice) {
    "1" { python test_connect.py; pause }
    "2" { python test_trade.py; pause }
    "3" { python ai_runner.py; pause }
    "4" {
        Write-Host "你可以修改ai_runner.py里DRY_RUN=False后运行" -ForegroundColor Red
        Write-Host "或者直接运行: python ai_runner.py" -ForegroundColor Yellow
        pause
    }
    default { Write-Host "已退出" }
}
