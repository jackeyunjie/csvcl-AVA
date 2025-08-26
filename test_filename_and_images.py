#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试文件名修复和图片嵌入功能
"""

import glob
import os
from email_sender import EmailSender

def test_filename_and_embedded_images():
    """
    测试文件名修复和图片嵌入功能
    """
    print("🔧 === 文件名修复 + 图片嵌入测试 ===\n")
    
    print("🎯 测试目标:")
    print("   ✅ 修复Excel文件名显示截断问题")
    print("   ✅ 使用RFC2047标准编码文件名")
    print("   ✅ 将截图直接嵌入邮件正文")
    print("   ✅ 不再作为附件发送图片\n")
    
    # 查找测试文件
    excel_files = sorted(glob.glob("*MT4_colored.xlsx"), key=os.path.getmtime, reverse=True)[:2]
    jpg_files = sorted(glob.glob("*MT4_screenshot.jpg"), key=os.path.getmtime, reverse=True)[:1]
    png_files = sorted(glob.glob("*MT4_screenshot.png"), key=os.path.getmtime, reverse=True)[:1]
    
    image_files = jpg_files + png_files
    
    if not excel_files and not image_files:
        print("❌ 没有找到测试文件")
        return
    
    print("📁 测试文件:")
    
    print("\n📊 Excel文件（作为附件）:")
    for i, excel_file in enumerate(excel_files, 1):
        size_kb = os.path.getsize(excel_file) / 1024
        filename = os.path.basename(excel_file)
        print(f"   {i}. {filename}")
        print(f"      大小: {size_kb:.1f}KB")
        print(f"      状态: 附件形式发送")
    
    print("\n🖼️ 截图文件（嵌入正文）:")
    for i, image_file in enumerate(image_files, 1):
        size_kb = os.path.getsize(image_file) / 1024
        filename = os.path.basename(image_file)
        ext = os.path.splitext(image_file)[1].upper()
        print(f"   {i}. {filename}")
        print(f"      大小: {size_kb:.1f}KB")
        print(f"      状态: 嵌入正文显示")
    
    # 设置收件人
    recipients = ["447372703@qq.com", "1300893414@qq.com"]
    
    print(f"\n📧 收件人: {', '.join(recipients)}")
    
    print(f"\n💡 新功能特点:")
    print(f"   ✅ Excel文件名使用UTF-8编码")
    print(f"   ✅ 图片直接显示在邮件中")
    print(f"   ✅ 无需下载即可查看截图")
    print(f"   ✅ 邮件更美观直观")
    
    send_test = input(f"\n是否发送测试邮件？(y/n): ").strip().lower()
    
    if send_test == 'y':
        print(f"\n🔄 开始发送测试邮件...")
        
        # 创建邮件发送器
        sender = EmailSender()
        
        # 发送邮件
        success = sender.send_mt4_report(
            excel_files=excel_files,
            image_files=image_files,
            recipients=recipients,
            subject="MT4数据文件 - 文件名修复+图片嵌入测试"
        )
        
        if success:
            print("\n✅ 测试邮件发送成功！")
            print("\n📥 请检查邮箱中的以下改进:")
            print("   1. Excel文件名是否显示完整")
            print("   2. 图片是否直接显示在邮件正文中")
            print("   3. 图片是否清晰可见")
            print("   4. 整体邮件是否更美观")
            
            print(f"\n🎯 预期效果:")
            for excel_file in excel_files:
                filename = os.path.basename(excel_file)
                print(f"   📊 {filename} - 完整文件名显示")
            for image_file in image_files:
                filename = os.path.basename(image_file)
                print(f"   🖼️ {filename} - 直接在正文中显示")
            
        else:
            print("❌ 测试邮件发送失败")
    
    else:
        print("⏭️ 跳过发送测试")

def show_technical_details():
    """
    显示技术改进细节
    """
    print("\n🔧 === 技术改进细节 ===")
    
    print("\n📝 文件名编码修复:")
    print("   原问题: 中文文件名显示截断")
    print("   解决方案: 使用RFC2047标准编码")
    print("   技术实现: Header(filename, 'utf-8').encode()")
    print("   效果: 支持完整的中文文件名显示")
    
    print("\n🖼️ 图片嵌入技术:")
    print("   原方式: 图片作为附件发送")
    print("   新方式: 图片嵌入邮件正文")
    print("   技术实现: Content-ID + HTML <img> 标签")
    print("   优势: 无需下载，直接查看")
    
    print("\n📧 邮件结构优化:")
    print("   邮件类型: MIMEMultipart('related')")
    print("   正文格式: HTML格式")
    print("   图片引用: cid:image1, cid:image2")
    print("   兼容性: 支持主流邮件客户端")

if __name__ == "__main__":
    test_filename_and_embedded_images()
    show_technical_details()