#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一测试入口

运行方式:
    python run_tests.py

本入口仅执行 tests/ 目录下的单元测试，不触发需要真实 MT4 数据、邮箱、
YouTube 或 MQL5 网络请求的集成测试脚本。
"""

import sys
import pytest

if __name__ == "__main__":
    args = ["tests/", "-v"] + sys.argv[1:]
    sys.exit(pytest.main(args))
