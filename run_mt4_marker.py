#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MT4文件颜色标记 - 简化版本
专门用于处理MT4文件夹中的KVBt_@_D1文件
"""

from csv_color_marker import CSVColorMarker

def main():
    """
    简化的主函数，直接使用预设参数
    """
    print("=== MT4 CSV文件颜色标记程序 ===")
    
    # 使用预设的MT4路径和参数
    marker = CSVColorMarker(
        search_path=r"C:\Users\MECHREVO\AppData\Roaming\MetaQuotes\Terminal\50D8083188871EAB17316B22F188CFF7\MQL4\Files",
        target_string="KVBt_@_D1",
        time_limit_minutes=7
    )
    
    marker.run()
    
    print("\n按任意键退出...")
    input()

if __name__ == "__main__":
    main()