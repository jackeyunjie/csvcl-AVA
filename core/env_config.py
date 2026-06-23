#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境变量与配置解析助手

本模块用于集中读取 .env / YAML 配置，避免在业务脚本中硬编码路径、邮箱等
敏感或易变信息。加载顺序（优先级从高到低）：

1. 环境变量
2. configs/mt4_config.yaml（或 MT4_CONFIG_PATH 指定的 YAML）
3. 调用方传入的默认值
"""

import os
from typing import List, Optional

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

from .config_manager import ConfigManager


_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_CONFIG_PATH = os.path.join(_PROJECT_ROOT, "configs", "mt4_config.yaml")


def _ensure_dotenv_loaded() -> None:
    """自动加载项目根目录下的 .env 文件（如果 python-dotenv 已安装）。"""
    if load_dotenv is None:
        return
    dotenv_path = os.path.join(_PROJECT_ROOT, ".env")
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path, override=False)


def _get_config_manager(config_path: Optional[str] = None) -> Optional[ConfigManager]:
    """延迟初始化 ConfigManager，避免在不需要时打印日志。"""
    path = config_path or os.environ.get("MT4_CONFIG_PATH") or _DEFAULT_CONFIG_PATH
    if not os.path.isabs(path):
        path = os.path.join(_PROJECT_ROOT, path)
    if os.path.exists(path):
        try:
            return ConfigManager(path)
        except Exception:
            return None
    return None


def get_mt4_files_path(default: Optional[str] = None,
                       config_path: Optional[str] = None) -> str:
    """
    获取 MT4 MQL4/Files 目录路径。

    Returns:
        路径字符串；如果没有任何来源则返回空字符串。
    """
    _ensure_dotenv_loaded()

    value = os.environ.get("MT4_FILES_PATH")
    if value:
        return os.path.expandvars(value)

    cfg = _get_config_manager(config_path)
    if cfg:
        paths = cfg.get("file_selection.search_paths", [])
        for p in paths:
            if p and isinstance(p, str):
                return os.path.expandvars(p)

    if default:
        return os.path.expandvars(default)

    return ""


def get_recipients(default: Optional[List[str]] = None,
                   config_path: Optional[str] = None) -> List[str]:
    """
    获取邮件收件人列表。支持逗号分隔的环境变量 EMAIL_RECIPIENTS。
    """
    _ensure_dotenv_loaded()

    value = os.environ.get("EMAIL_RECIPIENTS")
    if value:
        return [v.strip() for v in value.split(",") if v.strip()]

    cfg = _get_config_manager(config_path)
    if cfg:
        recipients = cfg.get("email.recipients", [])
        if recipients:
            return [str(r).strip() for r in recipients if r]

    return list(default) if default else []


def get_sender_name(default: str = "MT4数据处理系统") -> str:
    """获取发件人显示名称。"""
    _ensure_dotenv_loaded()
    return os.environ.get("EMAIL_SENDER_NAME") or default


def get_wiki_research_dir(default: Optional[str] = None) -> str:
    """获取 YouTube / MQL5 研究资料默认输出目录。"""
    _ensure_dotenv_loaded()

    value = os.environ.get("WIKI_RESEARCH_DIR")
    if value:
        return os.path.expandvars(value)

    if default:
        return os.path.expandvars(default)

    return os.path.join(_PROJECT_ROOT, "docs", "project-wiki", "raw", "research")


def get_project_root() -> str:
    """返回项目根目录绝对路径。"""
    return _PROJECT_ROOT


if __name__ == "__main__":
    print("MT4 path :", get_mt4_files_path())
    print("Recipients:", get_recipients())
    print("Wiki dir :", get_wiki_research_dir())
