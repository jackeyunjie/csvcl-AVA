#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试邮件中的颜色标注显示
"""

from csv_color_marker import CSVColorMarker
from email_sender import EmailSender
import os
import sys
import glob

def create_test_data():
    """创建测试数据文件"""
    print("创建测试数据...")
    
    # 使用debug_colors.py中的函数创建测试数据
    from debug_colors import create_test_csv
    test_file = create_test_csv()
    
    return test_file

def process_test_file(test_file):
    """处理测试文件，生成带颜色标注的Excel和图片"""
    print("\n处理测试文件...")
    
    # 初始化颜色标记器
    marker = CSVColorMarker()
    
    # 处理测试文件
    output_path = marker.process_csv_file(test_file)
    
    if not output_path:
        print("❌ 处理测试文件失败")
        return None, None
    
    # 查找生成的图片
    image_path = os.path.splitext(output_path)[0].replace('_colored', '_full_table') + '.png'
    
    if not os.path.exists(image_path):
        print(f"❌ 未找到图片文件: {image_path}")
        image_path = None
    
    return output_path, image_path

def send_test_email(excel_file, image_file):
    """发送测试邮件"""
    print("\n发送测试邮件...")
    
    if not excel_file or not image_file:
        print("❌ 缺少Excel文件或图片文件，无法发送邮件")
        return False
    
    # 初始化邮件发送器
    sender = EmailSender()
    
    # 检查配置
    if not os.path.exists("email_config.ini"):
        print("❌ 未找到邮件配置文件")
        print("请先创建email_config.ini文件，填入您的邮箱信息")
        return False
    
    # 获取收件人邮箱
    recipient = input("请输入收件人邮箱: ").strip()
    if not recipient:
        print("❌ 未提供收件人邮箱")
        return False
    
    # 发送邮件
    result = sender.send_mt4_report(
        excel_files=[excel_file],
        image_files=[image_file],
        recipients=[recipient],
        subject="颜色标注测试邮件"
    )
    
    return result

def main():
    """主函数"""
    print("=== 邮件颜色标注测试 ===")
    
    # 创建测试数据
    test_file = create_test_data()
    
    # 处理测试文件
    excel_file, image_file = process_test_file(test_file)
    
    if excel_file and image_file:
        print(f"\n✅ 文件处理成功")
        print(f"📊 Excel文件: {excel_file}")
        print(f"🖼️ 图片文件: {image_file}")
        
        # 询问是否发送测试邮件
        send_email = input("\n是否发送测试邮件？(y/n): ").strip().lower()
        if send_email == 'y':
            if send_test_email(excel_file, image_file):
                print("✅ 测试邮件发送成功！请检查收件箱")
            else:
                print("❌ 测试邮件发送失败")
    else:
        print("❌ 文件处理失败")

if __name__ == "__main__":
    main()