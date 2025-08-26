#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试附件修复功能
验证Excel和JPG文件能否正确作为附件发送
"""

import glob
import os
from email_sender import EmailSender

def test_attachment_fix():
    """
    测试修复后的附件发送功能
    """
    print("🔧 === 附件修复测试 ===\n")
    
    print("📋 测试目标:")
    print("   1. 修复.xlsx文件变成.bin的问题")
    print("   2. 修复.jpg文件变成.bin的问题")
    print("   3. 确保文件能正常下载和打开")
    print("   4. 验证文件大小和格式正确\n")
    
    # 查找测试文件
    excel_files = sorted(glob.glob("*MT4_colored.xlsx"), key=os.path.getmtime, reverse=True)[:2]
    jpg_files = sorted(glob.glob("*MT4_screenshot.jpg"), key=os.path.getmtime, reverse=True)[:2]
    png_files = sorted(glob.glob("*MT4_screenshot.png"), key=os.path.getmtime, reverse=True)[:1]
    
    image_files = jpg_files + png_files
    
    if not excel_files and not image_files:
        print("❌ 没有找到测试文件")
        return
    
    print("📁 找到的测试文件:")
    total_size = 0
    
    for i, excel_file in enumerate(excel_files, 1):
        size_kb = os.path.getsize(excel_file) / 1024
        total_size += size_kb
        print(f"   📊 {i}. {os.path.basename(excel_file)} ({size_kb:.1f}KB)")
        print(f"      类型: Excel工作簿 (.xlsx)")
    
    for i, image_file in enumerate(image_files, 1):
        size_kb = os.path.getsize(image_file) / 1024
        total_size += size_kb
        ext = os.path.splitext(image_file)[1].upper()
        print(f"   🖼️ {len(excel_files)+i}. {os.path.basename(image_file)} ({size_kb:.1f}KB)")
        print(f"      类型: 图片文件 ({ext})")
    
    print(f"\n📦 总附件大小: {total_size:.1f}KB")
    
    # 设置收件人
    recipients = ["447372703@qq.com", "1300893414@qq.com"]
    
    print(f"\n📧 收件人设置:")
    for i, recipient in enumerate(recipients, 1):
        print(f"   {i}. {recipient}")
    
    # 询问是否发送测试邮件
    print(f"\n🎯 测试说明:")
    print(f"   ✅ 使用改进的MIME类型设置")
    print(f"   ✅ 修复文件名编码问题")
    print(f"   ✅ 确保文件扩展名正确")
    print(f"   ✅ 添加正确的Content-Type头")
    
    send_test = input(f"\n是否发送附件修复测试邮件？(y/n): ").strip().lower()
    
    if send_test == 'y':
        print(f"\n🔄 开始发送测试邮件...")
        
        # 创建邮件发送器
        sender = EmailSender()
        
        # 发送邮件
        success = sender.send_mt4_report(
            excel_files=excel_files,
            image_files=image_files,
            recipients=recipients,
            subject="MT4数据报告 - 附件修复测试"
        )
        
        if success:
            print("\n✅ 测试邮件发送成功！")
            print("\n📥 请检查以下内容:")
            print("   1. 邮件是否正常接收")
            print("   2. 附件是否显示正确的文件名和图标")
            print("   3. Excel文件是否能正常打开")
            print("   4. 图片文件是否能正常查看")
            print("   5. 文件大小是否与发送端一致")
            
            print(f"\n🎯 预期结果:")
            for excel_file in excel_files:
                print(f"   📊 {os.path.basename(excel_file)} - 应显示为Excel文件")
            for image_file in image_files:
                ext = os.path.splitext(image_file)[1].upper()
                print(f"   🖼️ {os.path.basename(image_file)} - 应显示为{ext}图片文件")
            
        else:
            print("❌ 测试邮件发送失败")
            print("💡 请检查邮箱配置和网络连接")
    
    else:
        print("⏭️ 跳过发送测试")

def show_fix_details():
    """
    显示修复的技术细节
    """
    print("\n🔧 === 修复技术细节 ===")
    
    print("\n📊 Excel文件修复:")
    print("   原问题: MIME类型 application/octet-stream")
    print("   修复后: MIME类型 application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    print("   效果: 邮件客户端能正确识别为Excel文件")
    
    print("\n🖼️ 图片文件修复:")
    print("   原问题: 通用MIMEImage，缺少子类型")
    print("   修复后: 根据扩展名设置正确的image/jpeg或image/png")
    print("   效果: 邮件客户端能正确识别图片类型")
    
    print("\n📎 文件名修复:")
    print("   原问题: filename= filename.ext （格式不标准）")
    print("   修复后: filename=\"filename.ext\" （标准格式）")
    print("   效果: 避免文件名解析错误")
    
    print("\n🏷️ Content-Type头修复:")
    print("   原问题: 缺少Content-Type头信息")
    print("   修复后: 添加完整的Content-Type和name参数")
    print("   效果: 提高邮件客户端兼容性")

if __name__ == "__main__":
    test_attachment_fix()
    show_fix_details()