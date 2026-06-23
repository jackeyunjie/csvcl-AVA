#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MT4数据处理与邮件发送示例
演示如何使用邮件功能
"""

from process_real_mt4_data import RealMT4DataProcessor

def run_with_email_example():
    """
    运行带邮件发送功能的示例
    """
    print("🚀 === MT4数据处理与邮件发送示例 ===")
    
    # 示例收件人邮箱（请替换为实际邮箱）
    recipients = [
        "user1@example.com",
        "user2@example.com"
    ]
    
    # 创建处理器（启用邮件功能）
    processor = RealMT4DataProcessor(
        target_string="KVBt_@_D1",
        time_limit_minutes=300,  # 5小时内的文件
        enable_email=True,
        recipients=recipients
    )
    
    # 运行完整流程
    processor.run()

def run_without_email_example():
    """
    运行不带邮件发送功能的示例
    """
    print("🚀 === MT4数据处理示例（无邮件） ===")
    
    # 创建处理器（不启用邮件）
    processor = RealMT4DataProcessor(
        target_string="KVBt_@_D1",
        time_limit_minutes=300,
        enable_email=False
    )
    
    # 运行完整流程
    processor.run()

if __name__ == "__main__":
    print("请选择运行模式:")
    print("1. 带邮件发送功能")
    print("2. 不带邮件发送功能")
    
    choice = input("请输入选择 (1/2): ").strip()
    
    if choice == "1":
        print("\n⚠️  注意：使用邮件功能前，请先配置 email_config.ini 文件")
        run_with_email_example()
    elif choice == "2":
        run_without_email_example()
    else:
        print("❌ 无效选择")