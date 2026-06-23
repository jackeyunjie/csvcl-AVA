#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片保存功能测试脚本
"""

import os
from PIL import Image

def test_image_files():
    """
    测试生成的图片文件
    """
    print("=== 图片保存功能测试 ===")
    
    # 查找所有PNG图片文件
    png_files = [f for f in os.listdir('.') if f.endswith('.png')]
    
    if not png_files:
        print("❌ 未找到任何PNG图片文件")
        return
    
    print(f"📁 找到 {len(png_files)} 个PNG文件:")
    
    for png_file in png_files:
        try:
            # 打开图片
            img = Image.open(png_file)
            width, height = img.size
            mode = img.mode
            
            print(f"\n✅ {png_file}")
            print(f"   尺寸: {width} x {height} 像素")
            print(f"   模式: {mode}")
            print(f"   大小: {os.path.getsize(png_file)} 字节")
            
            # 验证图片是否可以正常读取
            if width > 0 and height > 0:
                print("   状态: ✅ 图片格式正常")
            else:
                print("   状态: ❌ 图片格式异常")
                
        except Exception as e:
            print(f"❌ {png_file}: 读取失败 - {str(e)}")
    
    print(f"\n=== 测试完成 ===")

if __name__ == "__main__":
    test_image_files()