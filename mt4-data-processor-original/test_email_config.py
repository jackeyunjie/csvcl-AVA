#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件配置测试脚本
测试当前邮箱配置是否可以正常连接
"""

import smtplib
import configparser
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def test_email_connection():
    """
    测试邮件服务器连接
    """
    print("📧 === 邮件配置测试 ===\n")
    
    # 读取配置
    config_file = "email_config.ini"
    if not os.path.exists(config_file):
        print("❌ 配置文件不存在")
        return False
    
    try:
        config = configparser.ConfigParser()
        config.read(config_file, encoding='utf-8')
        
        smtp_server = config.get('EMAIL', 'smtp_server')
        smtp_port = config.getint('EMAIL', 'smtp_port')
        username = config.get('EMAIL', 'username')
        password = config.get('EMAIL', 'password')
        sender_name = config.get('EMAIL', 'sender_name')
        
        print(f"📋 邮箱配置信息:")
        print(f"   服务器: {smtp_server}")
        print(f"   端口: {smtp_port}")
        print(f"   用户名: {username}")
        print(f"   发件人名称: {sender_name}")
        print(f"   密码: {'*' * len(password)}\n")
        
        # 测试连接
        print("🔄 正在测试连接...")
        
        if smtp_port == 465:
            # SSL连接
            print("   使用SSL连接...")
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            # TLS连接
            print("   使用TLS连接...")
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
        
        print("✅ 服务器连接成功")
        
        # 测试登录
        print("🔄 正在测试登录...")
        server.login(username, password)
        print("✅ 邮箱登录成功")
        
        # 关闭连接
        server.quit()
        print("✅ 连接测试完成\n")
        
        print("🎉 邮箱配置完全正确！可以发送邮件了！")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}\n")
        
        print("💡 可能的解决方案:")
        if "Authentication failed" in str(e):
            print("   - 检查用户名和密码是否正确")
            print("   - 如果是企业邮箱，确认密码是否正确")
        elif "Connection" in str(e):
            print("   - 检查网络连接")
            print("   - 检查服务器地址和端口")
            print("   - 尝试切换SSL/TLS模式")
        else:
            print("   - 联系邮箱管理员获取正确配置")
        
        return False

def send_test_email():
    """
    发送测试邮件
    """
    if not test_email_connection():
        return False
    
    print("\n📧 === 发送测试邮件 ===")
    
    recipient = input("请输入收件人邮箱（回车使用发件人邮箱）: ").strip()
    if not recipient:
        config = configparser.ConfigParser()
        config.read("email_config.ini", encoding='utf-8')
        recipient = config.get('EMAIL', 'username')
    
    try:
        config = configparser.ConfigParser()
        config.read("email_config.ini", encoding='utf-8')
        
        smtp_server = config.get('EMAIL', 'smtp_server')
        smtp_port = config.getint('EMAIL', 'smtp_port')
        username = config.get('EMAIL', 'username')
        password = config.get('EMAIL', 'password')
        sender_name = config.get('EMAIL', 'sender_name')
        
        # 创建测试邮件
        msg = MIMEMultipart()
        msg['From'] = username  # 使用简单格式
        msg['To'] = recipient
        msg['Subject'] = "MT4数据处理系统 - 邮件测试"
        
        body = """
        🎉 恭喜！邮件发送功能测试成功！
        
        📧 这是来自MT4数据处理系统的测试邮件
        ✅ 您的邮箱配置完全正确
        🚀 现在可以正常发送MT4数据报告了
        
        系统功能：
        - 自动处理MT4 CSV文件
        - 生成Excel文件并应用颜色标记
        - 生成A1:M40范围的完整截图
        - 自动发送邮件报告
        
        ---
        🤖 此邮件由MT4数据处理系统自动发送
        """
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # 发送邮件
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
        
        server.login(username, password)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ 测试邮件已发送到: {recipient}")
        print("🎉 邮件功能完全正常！")
        return True
        
    except Exception as e:
        print(f"❌ 发送测试邮件失败: {str(e)}")
        return False

if __name__ == "__main__":
    print("选择测试模式:")
    print("1. 仅测试连接")
    print("2. 测试连接并发送测试邮件")
    
    choice = input("请选择 (1/2): ").strip()
    
    if choice == "1":
        test_email_connection()
    elif choice == "2":
        send_test_email()
    else:
        print("❌ 无效选择")