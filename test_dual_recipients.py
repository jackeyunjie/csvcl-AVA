#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试双收件人邮件发送
验证向447372703@qq.com和1300893414@qq.com同时发送邮件
"""

import glob
import os
from email_sender import EmailSender

def test_dual_recipients_email():
    """
    测试向两个指定邮箱同时发送邮件
    """
    print("📧 === 双收件人邮件发送测试 ===\n")
    
    # 指定收件人
    recipients = [
        "447372703@qq.com",
        "1300893414@qq.com"
    ]
    
    print("📋 收件人配置:")
    for i, recipient in enumerate(recipients, 1):
        print(f"   {i}. {recipient}")
    
    # 查找最新的MT4文件
    excel_files = sorted(glob.glob("*MT4_colored.xlsx"), key=os.path.getmtime, reverse=True)[:2]
    image_files = sorted(glob.glob("*MT4_screenshot.png"), key=os.path.getmtime, reverse=True)[:2]
    
    if not excel_files and not image_files:
        print("\n❌ 没有找到MT4文件")
        return
    
    print(f"\n📁 准备发送的文件:")
    total_size = 0
    
    for i, excel_file in enumerate(excel_files, 1):
        size_kb = os.path.getsize(excel_file) / 1024
        total_size += size_kb
        print(f"   📊 {i}. {os.path.basename(excel_file)} ({size_kb:.1f}KB)")
    
    for i, image_file in enumerate(image_files, 1):
        size_kb = os.path.getsize(image_file) / 1024
        total_size += size_kb
        print(f"   🖼️  {len(excel_files)+i}. {os.path.basename(image_file)} ({size_kb:.1f}KB)")
    
    print(f"\n📦 总附件大小: {total_size:.1f}KB")
    
    # 创建邮件发送器
    sender = EmailSender()
    
    # 发送邮件（一次性发送给所有收件人）
    print(f"\n🔄 开始发送邮件...")
    success = sender.send_mt4_report(
        excel_files=excel_files,
        image_files=image_files,
        recipients=recipients,
        subject=f"MT4数据处理报告 - 双收件人测试"
    )
    
    if success:
        print("🎉 邮件发送成功！")
        print("📧 两个邮箱都应该收到相同的报告")
        print("📥 请检查两个邮箱查收邮件")
    else:
        print("❌ 邮件发送失败")
        print("💡 可能需要检查邮箱配置或网络连接")

if __name__ == "__main__":
    test_dual_recipients_email()