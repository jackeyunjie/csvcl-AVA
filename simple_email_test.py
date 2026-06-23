#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单邮件测试 - 测试附件发送
"""

import os
import sys
import shutil
import glob
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from email_sender import EmailSender

def find_latest_excel_file():
    """查找最新的MT4彩色Excel文件"""
    # 查找所有*_MT4_colored.xlsx文件
    excel_files = glob.glob("*_MT4_colored.xlsx")
    
    if not excel_files:
        print("❌ 未找到MT4 Excel文件")
        return None
        
    # 按创建时间排序
    excel_files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
    
    # 返回最新的文件
    latest_file = excel_files[0]
    print(f"📊 找到最新的MT4 Excel文件: {latest_file}")
    print(f"   创建时间: {datetime.fromtimestamp(os.path.getmtime(latest_file)).strftime('%Y-%m-%d %H:%M:%S')}")
    return latest_file

def find_latest_image_file():
    """查找最新的MT4截图文件"""
    # 查找所有*_MT4_screenshot.jpg文件
    image_files = glob.glob("*_MT4_screenshot.jpg")
    
    if not image_files:
        print("❌ 未找到MT4截图文件")
        return None
        
    # 按创建时间排序
    image_files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
    
    # 返回最新的文件
    latest_file = image_files[0]
    print(f"🖼️  找到最新的MT4截图文件: {latest_file}")
    print(f"   创建时间: {datetime.fromtimestamp(os.path.getmtime(latest_file)).strftime('%Y-%m-%d %H:%M:%S')}")
    return latest_file

def send_test_email():
    """发送测试邮件"""
    print("=== 简单邮件测试 ===")
    
    # 查找最新的Excel和截图文件
    excel_file = find_latest_excel_file()
    image_file = find_latest_image_file()
    
    if not excel_file:
        print("❌ 无法找到Excel文件，测试终止")
        return False
    
    # 初始化邮件发送器
    sender = EmailSender()
    
    # 验证配置
    if not sender.username or not sender.password:
        print("❌ 邮箱配置不完整，请检查配置文件")
        return False
    
    # 发送邮件
    recipients = ["447372703@qq.com", "1300893414@qq.com"]  # 发送给两个邮箱
    subject = f"MT4数据测试邮件 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    # 添加图片
    image_files = [image_file] if image_file else []
    
    # 发送邮件
    success = sender.send_mt4_report(
        excel_files=[excel_file],
        image_files=image_files,
        recipients=recipients,
        subject=subject
    )
    
    if success:
        print("✅ 测试邮件发送成功")
        print("请检查收件箱，验证附件是否正确")
        return True
    else:
        print("❌ 测试邮件发送失败")
        return False

if __name__ == "__main__":
    send_test_email()