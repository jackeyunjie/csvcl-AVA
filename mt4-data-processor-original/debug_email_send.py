#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件发送调试脚本
检查邮件发送的详细状态和可能的问题
"""

import smtplib
import configparser
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

def debug_email_send():
    """
    调试邮件发送问题
    """
    print("🔍 === 邮件发送调试分析 ===\n")
    
    # 读取配置
    config_file = "email_config.ini"
    if not os.path.exists(config_file):
        print("❌ 配置文件不存在")
        return
    
    config = configparser.ConfigParser()
    config.read(config_file, encoding='utf-8')
    
    smtp_server = config.get('EMAIL', 'smtp_server')
    smtp_port = config.getint('EMAIL', 'smtp_port')
    username = config.get('EMAIL', 'username')
    password = config.get('EMAIL', 'password')
    sender_name = config.get('EMAIL', 'sender_name')
    
    print(f"📋 当前邮箱配置:")
    print(f"   服务器: {smtp_server}")
    print(f"   端口: {smtp_port}")
    print(f"   发件人: {username}")
    print(f"   收件人: 1300893414@qq.com")
    print()
    
    # 分析可能的问题
    print("🔍 可能的问题分析:")
    print()
    
    print("1️⃣ 垃圾邮件文件夹检查:")
    print("   ✅ 请检查QQ邮箱的垃圾邮件文件夹")
    print("   ✅ 检查QQ邮箱的订阅邮件文件夹")
    print("   ✅ 检查广告邮件文件夹")
    print()
    
    print("2️⃣ 邮箱服务器问题:")
    print(f"   ⚠️  当前使用: {smtp_server}")
    print("   💡 企业邮箱可能有发送限制")
    print("   💡 可能被目标邮箱服务器拦截")
    print()
    
    print("3️⃣ 邮件大小问题:")
    print("   ⚠️  附件总大小约312KB")
    print("   💡 某些邮箱服务器可能限制附件大小")
    print()
    
    print("4️⃣ 发送频率问题:")
    print("   ⚠️  短时间内发送多封邮件")
    print("   💡 可能触发反垃圾邮件机制")
    print()

def send_simple_test_email():
    """
    发送简单的测试邮件（无附件）
    """
    print("📧 === 发送简单测试邮件（无附件） ===\n")
    
    try:
        config = configparser.ConfigParser()
        config.read("email_config.ini", encoding='utf-8')
        
        smtp_server = config.get('EMAIL', 'smtp_server')
        smtp_port = config.getint('EMAIL', 'smtp_port')
        username = config.get('EMAIL', 'username')
        password = config.get('EMAIL', 'password')
        sender_name = config.get('EMAIL', 'sender_name')
        
        # 让用户输入收件人邮箱
        recipient = input("请输入您的邮箱地址进行测试: ").strip()
        if not recipient:
            print("❌ 请提供收件人邮箱")
            return
        
        # 创建简单邮件
        msg = MIMEMultipart()
        msg['From'] = f"{sender_name} <{username}>"
        msg['To'] = recipient
        msg['Subject'] = f"MT4系统测试邮件 - {datetime.now().strftime('%H:%M:%S')}"
        
        body = f"""
        🔍 邮件发送测试

        发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        发件人: {username}
        收件人: {recipient}
        
        如果您收到此邮件，说明邮件发送功能正常！
        
        ✅ 请回复此邮件确认收到
        
        ---
        MT4数据处理系统
        """
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # 发送邮件
        print(f"🔄 正在发送测试邮件到: {recipient}")
        
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
            server.starttls()
        
        server.login(username, password)
        server.send_message(msg)
        server.quit()
        
        print("✅ 简单测试邮件发送成功！")
        print("📧 请检查您的邮箱（包括垃圾邮件文件夹）")
        print("💡 如果仍未收到，可能是邮箱服务器间的兼容性问题")
        
    except Exception as e:
        print(f"❌ 发送失败: {str(e)}")

def suggest_alternative_smtp():
    """
    建议替代的SMTP配置
    """
    print("🔧 === 替代SMTP配置建议 ===\n")
    
    print("如果当前企业邮箱发送有问题，建议尝试以下配置:")
    print()
    
    print("1️⃣ QQ邮箱配置:")
    print("   smtp_server = smtp.qq.com")
    print("   smtp_port = 587")
    print("   username = 您的QQ邮箱")
    print("   password = QQ邮箱授权码")
    print()
    
    print("2️⃣ 163邮箱配置:")
    print("   smtp_server = smtp.163.com") 
    print("   smtp_port = 465")
    print("   username = 您的163邮箱")
    print("   password = 163邮箱授权码")
    print()
    
    print("3️⃣ Gmail配置:")
    print("   smtp_server = smtp.gmail.com")
    print("   smtp_port = 587")
    print("   username = 您的Gmail")
    print("   password = 应用专用密码")
    print()

if __name__ == "__main__":
    print("请选择调试模式:")
    print("1. 问题分析")
    print("2. 发送简单测试邮件")
    print("3. 查看替代SMTP配置")
    
    choice = input("请选择 (1/2/3): ").strip()
    
    if choice == "1":
        debug_email_send()
    elif choice == "2":
        send_simple_test_email()
    elif choice == "3":
        suggest_alternative_smtp()
    else:
        print("❌ 无效选择")