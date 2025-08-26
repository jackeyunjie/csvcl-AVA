#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化邮件发送测试
只发送最新的几个文件
"""

import glob
import os
from email_sender import EmailSender

def send_latest_files():
    """
    发送最新的几个文件
    """
    print("📧 === 简化邮件发送测试 ===\n")
    
    # 查找最新的文件
    excel_files = sorted(glob.glob("*MT4_colored.xlsx"), key=os.path.getmtime, reverse=True)[:3]
    # 支持JPG和PNG两种格式的截图
    image_files_jpg = sorted(glob.glob("*MT4_screenshot.jpg"), key=os.path.getmtime, reverse=True)[:3]
    image_files_png = sorted(glob.glob("*MT4_screenshot.png"), key=os.path.getmtime, reverse=True)[:3]
    image_files = image_files_jpg + image_files_png
    image_files = sorted(image_files, key=os.path.getmtime, reverse=True)[:3]  # 只取最新3个
    
    print(f"📊 找到Excel文件: {len(excel_files)} 个")
    print(f"🖼️ 找到图片文件: {len(image_files)} 个\n")
    
    if not excel_files and not image_files:
        print("❌ 没有找到任何文件")
        return
    
    # 显示要发送的文件
    print("📁 将要发送的文件:")
    for i, excel_file in enumerate(excel_files, 1):
        size_kb = os.path.getsize(excel_file) / 1024
        print(f"   {i}. {excel_file} ({size_kb:.1f}KB)")
    
    for i, image_file in enumerate(image_files, 1):
        size_kb = os.path.getsize(image_file) / 1024
        print(f"   {len(excel_files)+i}. {image_file} ({size_kb:.1f}KB)")
    
    total_size = sum(os.path.getsize(f) for f in excel_files + image_files) / 1024
    print(f"\n📦 总附件大小: {total_size:.1f}KB\n")
    
    # 收件人邮箱
    recipients = ["1300893414@qq.com"]
    
    # 创建邮件发送器
    sender = EmailSender()
    
    # 发送邮件
    success = sender.send_mt4_report(
        excel_files=excel_files,
        image_files=image_files,
        recipients=recipients,
        subject=f"MT4数据处理报告 - 最新{len(excel_files)}个文件"
    )
    
    if success:
        print("🎉 邮件发送成功！")
        print("📧 请检查邮箱查收报告！")
    else:
        print("❌ 邮件发送失败")

if __name__ == "__main__":
    send_latest_files()