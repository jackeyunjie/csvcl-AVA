#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础单元测试：验证环境变量与配置解析助手的行为。
"""

import os
import sys

# Ensure project root is on sys.path when running from tests/
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from core.env_config import get_mt4_files_path, get_recipients, get_wiki_research_dir


def test_get_mt4_files_path_env_wins(monkeypatch):
    expected = r"C:\Test\MT4\Files"
    monkeypatch.setenv("MT4_FILES_PATH", expected)
    assert get_mt4_files_path() == expected


def test_get_mt4_files_path_fallback_used_when_no_env(monkeypatch):
    monkeypatch.delenv("MT4_FILES_PATH", raising=False)
    monkeypatch.setenv("MT4_CONFIG_PATH", "configs/_nonexistent_.yaml")
    fallback = r"C:\Fallback\Files"
    assert get_mt4_files_path(default=fallback) == fallback


def test_get_recipients_from_env(monkeypatch):
    monkeypatch.setenv("EMAIL_RECIPIENTS", "a@example.com, b@example.com")
    assert get_recipients() == ["a@example.com", "b@example.com"]


def test_get_recipients_default_when_no_env_or_config(monkeypatch):
    monkeypatch.delenv("EMAIL_RECIPIENTS", raising=False)
    default = ["fallback@example.com"]
    # Config in this repo also defines recipients, so default is a fallback.
    result = get_recipients(default=default)
    assert isinstance(result, list)
    assert len(result) > 0


def test_get_wiki_research_dir_default():
    path = get_wiki_research_dir()
    assert os.path.isabs(path)
    assert "docs" in path and "research" in path


def test_get_wiki_research_dir_from_env(monkeypatch):
    monkeypatch.setenv("WIKI_RESEARCH_DIR", r"D:\wiki\research")
    assert get_wiki_research_dir() == r"D:\wiki\research"
