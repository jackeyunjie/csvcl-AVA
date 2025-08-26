#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试数字0显示修复功能
"""

import os
import pandas as pd
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from process_real_mt4_data import RealMT4DataProcessor

def create_test_data_with_zeros():
    """
    创建包含数字0的测试数据
    """
    print("🔧 === 数字0显示测试 ===\n")
    
    print("📋 测试目标:")
    print("   ✅ 确保数字0能正确显示在截图中")
    print("   ✅ 验证修复后的显示逻辑")
    print("   ✅ 对比修复前后的效果\n")
    
    # 创建测试数据，包含大量的0
    test_data = {
        'SymbolName': ['HSI', 'SPX500', 'EURUSD', 'GBPUSD', 'TEST'],
        'TIME': ['2025.08.25 00:00', '2025.08.25 00:00', '2025.08.25 00:00', '2025.08.25 00:00', '2025.08.25 00:00'],
        'Period': ['@1440', '@1440', '@1440', '@1440', '@1440'],
        'PRICE': [25787.0, 6454.5, 1.0895, 1.2785, 100.0],
        'MN1': [2, 0, 0, 2, 0],  # 包含多个0
        'W1': [6, 0, 4, 0, 8],   # 包含多个0
        'D1': [4, 0, 0, 4, 0],   # 包含多个0
        'H4': [0, 0, 2, 0, 0],   # 全部是0
        'H1': [0, 0, 0, 0, 0],   # 全部是0
        'M30': [0, 0, 0, 0, 0],  # 全部是0
        'M15': [0, 0, 0, 0, 0],  # 全部是0
        'M5': [8, 0, -4, 0, 8],  # 包含多个0
        'M1': [-1, 0, 0, 6, 0]   # 包含多个0
    }
    
    df = pd.DataFrame(test_data)
    
    print("📊 测试数据（重点关注数字0）:")
    print(df.to_string())
    print(f"\n🔍 数字0统计:")
    
    # 统计E2:G40区域中的0的数量
    zero_count = 0
    for col in ['MN1', 'W1', 'D1']:  # E、F、G列
        zero_count += (df[col] == 0).sum()
    
    print(f"   E2:G40区域中有 {zero_count} 个数字0")
    
    return df

def test_zero_display():
    """
    测试数字0的显示功能
    """
    try:
        # 创建测试数据
        df = create_test_data_with_zeros()
        
        # 创建Excel工作簿
        wb = Workbook()
        ws = wb.active
        if ws is not None:
            ws.title = "Zero_Test_Data"
        
        # 将数据写入工作表
        if ws is not None:
            for r in dataframe_to_rows(df, index=False, header=True):
                ws.append(r)
        
        # 创建处理器
        processor = RealMT4DataProcessor()
        
        # 应用颜色格式
        if ws is not None:
            colored_count = processor.apply_color_formatting(df, ws, "E2:G40")
            print(f"\n✅ 颜色标记完成：共标记了 {colored_count} 个单元格")
            
            # 调整列宽
            processor.adjust_column_width(ws)
            print(f"✅ 列宽调整完成")
        
        # 保存Excel文件
        excel_filename = "zero_test_MT4_colored.xlsx"
        excel_path = os.path.join(os.path.dirname(__file__), excel_filename)
        wb.save(excel_path)
        print(f"✅ Excel文件已保存: {excel_filename}")
        
        # 生成截图
        if ws is not None:
            image_filename = "zero_test_MT4_screenshot.jpg"
            image_path = os.path.join(os.path.dirname(__file__), image_filename)
            
            result = processor.save_range_as_image(ws, "A1:M40", image_path, include_headers=True, image_format="JPG")
            
            if result:
                print(f"✅ 截图已保存: {image_filename}")
                
                # 分析文件大小
                file_size = os.path.getsize(image_path) / 1024
                print(f"\n📊 截图文件分析:")
                print(f"   📁 文件: {image_filename}")
                print(f"   📏 大小: {file_size:.1f}KB")
                print(f"   📐 格式: JPG")
                
                return excel_path, image_path
            else:
                print("❌ 截图生成失败")
                return excel_path, None
        
    except Exception as e:
        print(f"❌ 测试过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None

def verify_zero_display():
    """
    验证数字0显示效果
    """
    print(f"\n🔍 === 验证数字0显示效果 ===")
    
    print(f"\n💡 修复说明:")
    print(f"   原问题: if cell_value: # 数字0被当作False")
    print(f"   修复后: if cell_value is not None and str(cell_value).strip() != \"\"")
    print(f"   效果: 数字0现在能正确显示")
    
    print(f"\n📋 检查要点:")
    print(f"   1. Excel文件中数字0是否存在")
    print(f"   2. 截图中数字0是否清晰可见")
    print(f"   3. 颜色标记是否正确应用到0值单元格")
    print(f"   4. 行列边框是否正常显示")

if __name__ == "__main__":
    print("🚀 开始数字0显示测试...\n")
    
    excel_path, image_path = test_zero_display()
    
    if excel_path and image_path:
        print(f"\n🎉 测试完成！")
        print(f"\n📁 生成文件:")
        print(f"   📊 Excel: {os.path.basename(excel_path)}")
        print(f"   🖼️ 截图: {os.path.basename(image_path)}")
        
        verify_zero_display()
        
        print(f"\n👀 请检查生成的截图，确认:")
        print(f"   ✅ 数字0是否清晰显示")
        print(f"   ✅ H4、H1、M30、M15列的所有0是否可见")
        print(f"   ✅ 其他列中的0是否正常显示")
        
    else:
        print(f"\n❌ 测试失败，请检查错误信息")