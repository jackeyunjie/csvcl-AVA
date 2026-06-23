#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MT4文件颜色标记 - 简化版本
专门用于处理MT4文件夹中的KVBt_@_D1文件
"""

from csv_color_marker import CSVColorMarker
from core.env_config import get_mt4_files_path

def main():
    """
    简化的主函数，直接使用预设参数
    """
    print("=== MT4 CSV文件颜色标记程序 ===")
    
    # 使用环境变量 / YAML 配置中的 MT4 路径，避免硬编码
    marker = CSVColorMarker(
        search_path=get_mt4_files_path(),
        target_string="KVBt_@_D1",
        time_limit_minutes=7
    )
    
    marker.run()
    
    print("\n按任意键退出...")
    input()

if __name__ == "__main__":
    main()