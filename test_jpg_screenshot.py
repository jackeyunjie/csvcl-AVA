#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JPG格式截图功能测试
"""

from process_real_mt4_data import RealMT4DataProcessor
import os
import glob

def test_jpg_screenshot():
    """
    测试JPG格式的截图功能
    """
    print("🖼️ === JPG格式截图功能测试 ===\n")
    
    print("📋 测试内容:")
    print("   1. 生成JPG格式的MT4数据截图")
    print("   2. 验证文件大小和质量")
    print("   3. 对比JPG vs PNG的文件大小")
    print("   4. 测试邮件发送功能\n")
    
    # 创建处理器（不启用邮件）
    processor = RealMT4DataProcessor(
        target_string="KVBt_@_D1",
        time_limit_minutes=360,  # 6小时内的文件
        enable_email=False
    )
    
    # 查找MT4文件
    print("🔄 正在查找MT4文件...")
    mt4_files = processor.find_real_mt4_files()
    
    if not mt4_files:
        print("❌ 未找到符合条件的MT4文件")
        print("💡 尝试增加时间范围或检查文件名")
        return
    
    # 处理第一个文件
    print(f"📄 处理文件: {os.path.basename(mt4_files[0])}")
    excel_path, image_path = processor.process_real_csv_data(mt4_files[0])
    
    if image_path and os.path.exists(image_path):
        print(f"\n✅ JPG截图生成成功！")
        
        # 分析文件信息
        file_size = os.path.getsize(image_path)
        print(f"📊 文件分析:")
        print(f"   📁 文件路径: {image_path}")
        print(f"   📏 文件大小: {file_size:,} 字节 ({file_size/1024:.1f} KB)")
        
        # 使用PIL分析图片
        from PIL import Image
        with Image.open(image_path) as img:
            print(f"   📐 图片尺寸: {img.size[0]} x {img.size[1]} 像素")
            print(f"   🎨 图片模式: {img.mode}")
            print(f"   📝 图片格式: {img.format}")
        
        # 对比PNG格式（如果存在）
        png_path = image_path.replace('.jpg', '.png')
        if os.path.exists(png_path):
            png_size = os.path.getsize(png_path)
            print(f"\n📊 格式对比:")
            print(f"   JPG大小: {file_size:,} 字节")
            print(f"   PNG大小: {png_size:,} 字节")
            print(f"   压缩率: {((png_size - file_size) / png_size * 100):.1f}% 更小")
        
        print(f"\n🎯 JPG格式优势:")
        print(f"   ✅ 文件更小，节省存储空间")
        print(f"   ✅ 邮件发送更快")
        print(f"   ✅ 适合大量数据截图")
        print(f"   ✅ 质量设置为95%，保持清晰度")
        
    else:
        print("❌ JPG截图生成失败")

def test_jpg_email_sending():
    """
    测试JPG格式截图的邮件发送
    """
    print("\n📧 === JPG截图邮件发送测试 ===")
    
    # 查找最新的JPG文件
    jpg_files = sorted(glob.glob("*MT4_screenshot.jpg"), key=os.path.getmtime, reverse=True)[:2]
    excel_files = sorted(glob.glob("*MT4_colored.xlsx"), key=os.path.getmtime, reverse=True)[:2]
    
    if not jpg_files:
        print("❌ 未找到JPG截图文件")
        return
    
    print(f"📁 找到 {len(jpg_files)} 个JPG截图文件:")
    total_size = 0
    for i, jpg_file in enumerate(jpg_files, 1):
        size_kb = os.path.getsize(jpg_file) / 1024
        total_size += size_kb
        print(f"   {i}. {os.path.basename(jpg_file)} ({size_kb:.1f}KB)")
    
    for i, excel_file in enumerate(excel_files, 1):
        size_kb = os.path.getsize(excel_file) / 1024
        total_size += size_kb
        print(f"   {len(jpg_files)+i}. {os.path.basename(excel_file)} ({size_kb:.1f}KB)")
    
    print(f"\n📦 总附件大小: {total_size:.1f}KB")
    
    # 询问是否发送邮件
    send_email = input("\n是否发送测试邮件？(y/n): ").strip().lower()
    
    if send_email == 'y':
        from email_sender import EmailSender
        sender = EmailSender()
        
        recipients = ["447372703@qq.com", "1300893414@qq.com"]
        
        success = sender.send_mt4_report(
            excel_files=excel_files,
            image_files=jpg_files,
            recipients=recipients,
            subject="MT4数据处理报告 - JPG格式截图测试"
        )
        
        if success:
            print("✅ JPG格式截图邮件发送成功！")
            print("📧 请检查邮箱查收")
        else:
            print("❌ 邮件发送失败")
    else:
        print("⏭️ 跳过邮件发送测试")

if __name__ == "__main__":
    test_jpg_screenshot()
    test_jpg_email_sending()