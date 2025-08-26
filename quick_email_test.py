#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速邮件功能测试
运行完整的MT4数据处理和邮件发送
"""

from process_real_mt4_data import RealMT4DataProcessor

def quick_email_demo():
    """
    快速演示邮件发送功能
    """
    print("🚀 === MT4数据处理 + 邮件发送演示 ===\n")
    
    # 设置收件人邮箱（请替换为您的实际邮箱）
    recipients = [
        "your_email@qq.com",  # 请替换为您的邮箱
        # "friend@example.com",  # 可以添加更多收件人
    ]
    
    print("📧 邮件功能说明:")
    print("✅ 自动发送Excel文件和截图")
    print("✅ 包含完整的HTML格式报告")
    print("✅ 支持多个收件人")
    print("✅ 自动附加所有生成的文件\n")
    
    print("⚠️  使用前请先配置邮箱:")
    print("1. 编辑 email_config.ini 文件")
    print("2. 填入您的邮箱和授权码")
    print("3. 修改上面的 recipients 邮箱地址\n")
    
    # 询问是否继续
    choice = input("是否继续运行？(y/n): ").strip().lower()
    
    if choice == 'y':
        print("\n🔄 开始处理...")
        
        # 创建处理器（启用邮件功能）
        processor = RealMT4DataProcessor(
            target_string="KVBt_@_D1",
            time_limit_minutes=300,  # 5小时内的文件
            enable_email=True,
            recipients=recipients
        )
        
        # 运行完整流程
        processor.run()
        
        print("\n🎉 处理完成！")
        print("📧 如果邮箱配置正确，邮件已发送")
        
    else:
        print("❌ 已取消运行")

if __name__ == "__main__":
    quick_email_demo()