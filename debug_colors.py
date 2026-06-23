#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试颜色标注问题
验证颜色标注是否正确保存到图片中
"""

from csv_color_marker import CSVColorMarker
import os
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font
import sys

def create_test_csv():
    """创建测试CSV文件，包含所有可能的颜色值"""
    print("创建测试CSV文件...")
    
    # 创建包含所有颜色值的测试数据
    data = {
        'A': ['Header', 'Red1', 'Red2', 'Red3', 'Red4', 'Red5', 'Red6', 
              'LightRed1', 'LightRed2', 'LightRed3', 'LightRed4', 'LightRed5', 'LightRed6',
              'Green1', 'Green2', 'Green3', 'Green4', 'Green5', 'Green6',
              'LightGreen1', 'LightGreen2', 'LightGreen3', 'LightGreen4', 'LightGreen5', 'LightGreen6',
              'Yellow'],
        'B': ['Value', 'Test', 'Test', 'Test', 'Test', 'Test', 'Test',
              'Test', 'Test', 'Test', 'Test', 'Test', 'Test',
              'Test', 'Test', 'Test', 'Test', 'Test', 'Test',
              'Test', 'Test', 'Test', 'Test', 'Test', 'Test',
              'Test'],
        'C': ['Description', 'Red color', 'Red color', 'Red color', 'Red color', 'Red color', 'Red color',
              'Light red', 'Light red', 'Light red', 'Light red', 'Light red', 'Light red',
              'Green color', 'Green color', 'Green color', 'Green color', 'Green color', 'Green color',
              'Light green', 'Light green', 'Light green', 'Light green', 'Light green', 'Light green',
              'Yellow color'],
        'D': ['Test', 'Value', 'Value', 'Value', 'Value', 'Value', 'Value',
              'Value', 'Value', 'Value', 'Value', 'Value', 'Value',
              'Value', 'Value', 'Value', 'Value', 'Value', 'Value',
              'Value', 'Value', 'Value', 'Value', 'Value', 'Value',
              'Value'],
        'E': ['E', 2, 3, 4, 5, 6, 7,
              10, 11, 12, 13, 14, 15,
              -2, -3, -4, -5, -6, -7,
              -10, -11, -12, -13, -14, -15,
              8],
        'F': ['F', 2, 3, 4, 5, 6, 7,
              10, 11, 12, 13, 14, 15,
              -2, -3, -4, -5, -6, -7,
              -10, -11, -12, -13, -14, -15,
              8],
        'G': ['G', 2, 3, 4, 5, 6, 7,
              10, 11, 12, 13, 14, 15,
              -2, -3, -4, -5, -6, -7,
              -10, -11, -12, -13, -14, -15,
              8]
    }
    
    # 创建DataFrame
    df = pd.DataFrame(data)
    
    # 保存为CSV
    test_file = "test_color_debug.csv"
    df.to_csv(test_file, index=False)
    print(f"✅ 测试文件已创建: {test_file}")
    
    return test_file

def test_color_marker():
    """测试颜色标记功能"""
    print("\n=== 测试颜色标记功能 ===")
    
    # 创建测试文件
    test_file = create_test_csv()
    
    # 初始化颜色标记器
    marker = CSVColorMarker()
    
    # 处理测试文件
    print("\n处理测试文件...")
    output_path = marker.process_csv_file(test_file)
    
    if output_path:
        print(f"\n✅ 测试成功！")
        print(f"📊 生成的Excel文件: {output_path}")
        print(f"🖼️ 生成的图片: {os.path.splitext(output_path)[0].replace('_colored', '_full_table')}.png")
        print("\n请检查生成的图片是否包含正确的颜色标注")
        
        # 尝试打开生成的Excel文件
        try:
            print("\n尝试打开Excel文件...")
            import subprocess
            import platform
            
            if platform.system() == 'Windows':
                os.startfile(output_path)
                print("✅ Excel文件已打开")
            elif platform.system() == 'Darwin':  # macOS
                subprocess.call(['open', output_path])
                print("✅ Excel文件已打开")
            else:  # Linux
                subprocess.call(['xdg-open', output_path])
                print("✅ Excel文件已打开")
        except Exception as e:
            print(f"❌ 无法自动打开Excel文件: {str(e)}")
            print(f"请手动打开文件: {output_path}")
    else:
        print("❌ 测试失败！未能生成Excel文件")

def verify_image_colors():
    """验证图片中的颜色是否正确"""
    print("\n=== 验证图片颜色 ===")
    
    # 查找最新的图片文件
    import glob
    image_files = glob.glob("*_full_table.png")
    
    if not image_files:
        print("❌ 未找到图片文件")
        return
    
    # 按修改时间排序，获取最新的图片
    latest_image = max(image_files, key=os.path.getmtime)
    print(f"找到最新图片: {latest_image}")
    
    # 尝试打开图片
    try:
        print("\n尝试打开图片...")
        import subprocess
        import platform
        
        if platform.system() == 'Windows':
            os.startfile(latest_image)
            print("✅ 图片已打开")
        elif platform.system() == 'Darwin':  # macOS
            subprocess.call(['open', latest_image])
            print("✅ 图片已打开")
        else:  # Linux
            subprocess.call(['xdg-open', latest_image])
            print("✅ 图片已打开")
    except Exception as e:
        print(f"❌ 无法自动打开图片: {str(e)}")
        print(f"请手动打开图片: {latest_image}")

if __name__ == "__main__":
    print("=== 颜色标注调试工具 ===")
    test_color_marker()
    verify_image_colors()
    print("\n调试完成！")