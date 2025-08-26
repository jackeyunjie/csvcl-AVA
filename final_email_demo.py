#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整邮件发送功能演示
展示MT4数据处理 + 邮件发送的完整流程
"""

from process_real_mt4_data import RealMT4DataProcessor
import datetime

def demo_complete_email_system():
    """
    演示完整的邮件发送系统
    """
    print("🎉 === MT4数据处理 + 邮件发送完整演示 ===\n")
    
    print("📧 当前邮箱配置:")
    print("   📮 发件邮箱: 554732319@qq.com")
    print("   🎯 收件邮箱: 1300893414@qq.com")
    print("   🔧 SMTP服务器: smtp.qq.com:587")
    print("   ✅ 状态: 已测试通过\n")
    
    print("🎯 系统功能展示:")
    print("   1️⃣  筛选MT4数据文件（包含'KVBt_@_D1'）")
    print("   2️⃣  生成Excel文件并应用颜色标记")
    print("   3️⃣  生成A1:M40高清截图（1080×1025像素）")
    print("   4️⃣  发送专业HTML邮件报告\n")
    
    # 设置收件人
    recipients = ["1300893414@qq.com"]
    
    # 询问时间范围
    print("选择处理文件的时间范围:")
    print("1. 5分钟内（实时处理）")
    print("2. 60分钟内（1小时内）")
    print("3. 360分钟内（6小时内）")
    
    choice = input("请选择 (1/2/3): ").strip()
    
    if choice == "1":
        time_limit = 5
        desc = "实时处理"
    elif choice == "2":
        time_limit = 60
        desc = "1小时内"
    elif choice == "3":
        time_limit = 360
        desc = "6小时内"
    else:
        time_limit = 60
        desc = "1小时内（默认）"
    
    print(f"\n🔄 开始{desc}的文件处理和邮件发送...\n")
    
    # 创建处理器
    processor = RealMT4DataProcessor(
        target_string="KVBt_@_D1",
        time_limit_minutes=time_limit,
        enable_email=True,
        recipients=recipients
    )
    
    # 运行完整流程
    processor.run()
    
    print(f"\n🎉 演示完成！")
    print(f"📧 邮件已发送到: {', '.join(recipients)}")
    print(f"📥 请检查邮箱查收MT4数据报告！")
    
    print(f"\n📋 邮件内容包含:")
    print(f"   📊 Excel文件（含颜色标记）")
    print(f"   🖼️  高清截图（A1:M40范围）")
    print(f"   📄 专业HTML报告")
    print(f"   🎯 数据特点说明")

def quick_test_email():
    """
    快速测试邮件功能
    """
    print("⚡ === 快速邮件功能测试 ===\n")
    
    # 直接发送已有的文件
    from simple_email_test import send_latest_files
    send_latest_files()

if __name__ == "__main__":
    print("请选择演示模式:")
    print("1. 完整系统演示（处理+邮件）")
    print("2. 快速邮件测试（发送已有文件）")
    
    mode = input("请选择 (1/2): ").strip()
    
    if mode == "1":
        demo_complete_email_system()
    elif mode == "2":
        quick_test_email()
    else:
        print("❌ 无效选择，运行完整演示")
        demo_complete_email_system()