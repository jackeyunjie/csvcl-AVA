#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MT4数据处理 + 邮件发送完整演示
使用已有文件进行邮件发送测试
"""

from process_real_mt4_data import RealMT4DataProcessor

def demo_email_with_existing_files():
    """
    使用现有文件演示邮件发送功能
    """
    print("🚀 === MT4数据处理 + 邮件发送完整演示 ===\n")
    
    # 设置收件人邮箱
    recipients = [
        "1300893414@qq.com",  # 使用刚才测试成功的邮箱
    ]
    
    print("📧 邮件发送演示:")
    print("✅ 使用已验证的邮箱配置")
    print("✅ 处理最近的MT4文件")
    print("✅ 生成Excel和截图")
    print("✅ 发送完整邮件报告\n")
    
    # 创建处理器（使用更长时间范围，启用邮件）
    processor = RealMT4DataProcessor(
        target_string="KVBt_@_D1",
        time_limit_minutes=360,  # 6小时内的文件
        enable_email=True,
        recipients=recipients
    )
    
    print("🔄 开始处理和发送邮件...")
    
    # 运行完整流程
    processor.run()
    
    print("\n🎉 演示完成！")
    print("📧 邮件应该已经成功发送到: 1300893414@qq.com")
    print("📥 请检查邮箱查收MT4数据报告！")

if __name__ == "__main__":
    demo_email_with_existing_files()