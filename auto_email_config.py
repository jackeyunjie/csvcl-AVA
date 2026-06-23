#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动邮件发送配置
每天7:00-22:00时段生成的MT4数据自动发送到指定邮箱
"""

from datetime import datetime, time
from process_real_mt4_data import RealMT4DataProcessor
from core.env_config import get_recipients

# 邮件发送配置（优先从环境变量 / YAML 配置读取）
EMAIL_RECIPIENTS = get_recipients(default=[
    "447372703@qq.com",
    "1300893414@qq.com"
])

# 发送时间配置（7:00-22:00）
SEND_TIME_START = time(7, 0)   # 7:00
SEND_TIME_END = time(22, 0)    # 22:00

def should_send_email():
    """
    判断当前时间是否应该发送邮件
    发送时间段：7:00-22:00
    """
    current_time = datetime.now().time()
    
    # 检查是否在发送时间段内（7:00-22:00）
    return SEND_TIME_START <= current_time <= SEND_TIME_END

def get_email_recipients():
    """
    获取邮件收件人列表
    """
    return EMAIL_RECIPIENTS.copy()

def create_auto_processor():
    """
    创建自动邮件发送处理器
    """
    # 判断是否启用邮件发送
    enable_email = should_send_email()
    
    current_hour = datetime.now().hour
    current_minute = datetime.now().minute
    
    print(f"🕐 当前时间: {current_hour:02d}:{current_minute:02d}")
    
    if enable_email:
        print("✅ 当前时间在发送时段（7:00-22:00），将启用邮件发送功能")
        recipients = get_email_recipients()
        print(f"📧 收件人: {', '.join(recipients)}")
    else:
        print("⏰ 当前时间不在发送时段内，不发送邮件")
        print("📅 发送时段: 7:00-22:00")
        recipients = None
    
    # 创建处理器
    processor = RealMT4DataProcessor(
        target_string="KVBt_@_D1",
        time_limit_minutes=10,  # 10分钟内的文件
        enable_email=enable_email,
        recipients=recipients
    )
    
    return processor

def run_auto_email_system():
    """
    运行自动邮件发送系统
    """
    print("🚀 === 自动邮件发送系统启动 ===\n")
    
    print("📋 配置信息:")
    for idx, recipient in enumerate(EMAIL_RECIPIENTS, start=1):
        print(f"   📮 收件人{idx}: {recipient}")
    print(f"   ⏰ 发送时段: 7:00-22:00")
    print(f"   📂 处理文件: 包含'KVBt_@_D1'的MT4数据")
    print()
    
    # 创建并运行处理器
    processor = create_auto_processor()
    processor.run()
    
    print("\n🎉 自动邮件发送系统运行完成！")

if __name__ == "__main__":
    run_auto_email_system()