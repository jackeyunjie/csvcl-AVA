#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试简化邮件发送功能
只发送附件，没有复杂的HTML报告
"""

import glob
import os
from email_sender import EmailSender

def test_simple_email():
    """
    测试简化后的邮件发送功能
    """
    print("📧 === 简化邮件发送测试 ===\n")
    
    print("🎯 测试目标:")
    print("   ✅ 去掉复杂的HTML数据报告")
    print("   ✅ 只发送简单文字说明")
    print("   ✅ 重点突出附件文件")
    print("   ✅ 确保附件正常打开\n")
    
    # 查找最新的文件
    excel_files = sorted(glob.glob("*MT4_colored.xlsx"), key=os.path.getmtime, reverse=True)[:2]
    jpg_files = sorted(glob.glob("*MT4_screenshot.jpg"), key=os.path.getmtime, reverse=True)[:1]
    png_files = sorted(glob.glob("*MT4_screenshot.png"), key=os.path.getmtime, reverse=True)[:1]
    
    image_files = jpg_files + png_files
    
    if not excel_files and not image_files:
        print("❌ 没有找到测试文件")
        return
    
    print("📁 将要发送的文件:")
    total_size = 0
    
    for i, excel_file in enumerate(excel_files, 1):
        size_kb = os.path.getsize(excel_file) / 1024
        total_size += size_kb
        print(f"   📊 {i}. {os.path.basename(excel_file)} ({size_kb:.1f}KB)")
    
    for i, image_file in enumerate(image_files, 1):
        size_kb = os.path.getsize(image_file) / 1024
        total_size += size_kb
        ext = os.path.splitext(image_file)[1].upper()
        print(f"   🖼️ {len(excel_files)+i}. {os.path.basename(image_file)} ({size_kb:.1f}KB)")
    
    print(f"\n📦 总附件大小: {total_size:.1f}KB")
    
    # 设置收件人
    recipients = ["447372703@qq.com", "1300893414@qq.com"]
    
    print(f"\n📧 收件人: {', '.join(recipients)}")
    
    # 询问是否发送测试邮件
    print(f"\n💡 简化邮件特点:")
    print(f"   ✅ 纯文字格式，无HTML")
    print(f"   ✅ 简洁的文件列表")
    print(f"   ✅ 重点突出附件")
    print(f"   ✅ 加载速度更快")
    
    send_test = input(f"\n是否发送简化邮件测试？(y/n): ").strip().lower()
    
    if send_test == 'y':
        print(f"\n🔄 开始发送简化邮件...")
        
        # 创建邮件发送器
        sender = EmailSender()
        
        # 发送邮件
        success = sender.send_mt4_report(
            excel_files=excel_files,
            image_files=image_files,
            recipients=recipients,
            subject="MT4数据文件"
        )
        
        if success:
            print("\n✅ 简化邮件发送成功！")
            print("\n📥 请检查邮箱:")
            print("   1. 邮件内容是否简洁清晰")
            print("   2. 附件是否正常显示")
            print("   3. 文件是否能正常打开")
            print("   4. 加载速度是否更快")
            
        else:
            print("❌ 邮件发送失败")
    
    else:
        print("⏭️ 跳过发送测试")

if __name__ == "__main__":
    test_simple_email()