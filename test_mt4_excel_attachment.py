#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MT4数据附件发送问题修复测试
专门用于验证修复后的邮件附件功能
"""

import os
import sys
import shutil
from datetime import datetime
from email.mime.multipart import MIMEMultipart

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from email_sender import EmailSender
from process_real_mt4_data import RealMT4DataProcessor

def verify_excel_file(file_path):
    """验证Excel文件是否存在且格式正确"""
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return False
    
    # 检查文件大小
    file_size = os.path.getsize(file_path)
    if file_size < 1000:  # 太小的文件可能不是有效的Excel
        print(f"❌ 文件太小 ({file_size} 字节)，可能不是有效的Excel文件")
        return False
    
    # 检查文件扩展名
    if not file_path.endswith('.xlsx'):
        print(f"❌ 文件扩展名不是.xlsx")
        return False
    
    print(f"✅ Excel文件验证通过: {os.path.basename(file_path)}")
    print(f"   文件大小: {file_size/1024:.1f} KB")
    return True

def find_latest_mt4_excel():
    """查找最新的MT4 Excel文件"""
    excel_files = [f for f in os.listdir('.') if f.endswith('_MT4_colored.xlsx')]
    if not excel_files:
        print("❌ 未找到MT4 Excel文件")
        return None
    
    # 按修改时间排序，获取最新的文件
    excel_files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
    latest_file = excel_files[0]
    print(f"📊 找到最新的MT4 Excel文件: {latest_file}")
    return latest_file

def find_latest_mt4_image():
    """查找最新的MT4截图文件"""
    image_files = [f for f in os.listdir('.') if f.endswith('_MT4_screenshot.jpg')]
    if not image_files:
        print("❌ 未找到MT4截图文件")
        return None
    
    # 按修改时间排序，获取最新的文件
    image_files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
    latest_file = image_files[0]
    print(f"🖼️ 找到最新的MT4截图文件: {latest_file}")
    return latest_file

def test_send_mt4_excel(excel_file=None):
    """测试发送MT4 Excel文件"""
    print("=== 测试发送MT4 Excel文件 ===")
    
    # 如果未提供Excel文件，则查找最新的文件
    if not excel_file:
        excel_file = find_latest_mt4_excel()
        if not excel_file:
            return False
    
    # 验证Excel文件
    if not verify_excel_file(excel_file):
        return False
    
    # 创建一个备份文件，以防原文件被修改
    backup_file = f"test_backup_{os.path.basename(excel_file)}"
    shutil.copy2(excel_file, backup_file)
    print(f"📄 已创建备份文件: {backup_file}")
    
    # 查找对应的截图文件
    image_file = find_latest_mt4_image()
    
    # 创建邮件发送器
    print("📧 创建邮件发送器...")
    sender = EmailSender()
    
    # 检查配置
    if not sender.username or not sender.password:
        print("❌ 邮箱配置不完整，请检查email_config.ini文件")
        return False
    
    # 定义测试收件人
    recipients = ["447372703@qq.com"]  # 可以修改为其他测试邮箱
    
    # 创建测试主题，包含时间戳以便区分不同测试
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    subject = f"MT4数据Excel附件测试 - {timestamp}"
    
    # 发送邮件
    print(f"📧 发送测试邮件...")
    print(f"   发件人: {sender.username}")
    print(f"   收件人: {', '.join(recipients)}")
    print(f"   主题: {subject}")
    print(f"   Excel附件: {os.path.basename(backup_file)}")
    if image_file:
        print(f"   图片附件: {os.path.basename(image_file)}")
    
    # 准备发送文件列表
    excel_files = [backup_file]
    image_files = [image_file] if image_file else []
    
    # 发送邮件
    success = sender.send_mt4_report(
        excel_files=excel_files,
        image_files=image_files,
        recipients=recipients,
        subject=subject,
        data_changes=[]  # 不添加数据变化以简化测试
    )
    
    if success:
        print("✅ 测试邮件发送成功!")
        print("请检查收件箱，验证邮件附件中的Excel文件是否正确显示MT4数据和颜色标记")
        return True
    else:
        print("❌ 测试邮件发送失败!")
        return False

def main():
    """主函数"""
    print("=== MT4数据邮件附件问题修复测试 ===")
    print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 如果指定了文件路径，则使用指定的文件
    if len(sys.argv) > 1:
        excel_file = sys.argv[1]
        test_send_mt4_excel(excel_file)
    else:
        test_send_mt4_excel()
    
    print("\n测试完成后：")
    print("1. 请检查邮箱收件箱")
    print("2. 确认Excel附件能否正常打开")
    print("3. 验证是否显示正确的MT4数据和颜色标记")

if __name__ == "__main__":
    main()