#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QQ邮箱配置向导
帮助配置可靠的QQ邮箱发送功能
"""

import configparser
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

def setup_qq_email():
    """
    配置QQ邮箱
    """
    print("📧 === QQ邮箱配置向导 ===\n")
    
    print("📋 配置步骤:")
    print("1. 登录QQ邮箱网页版 (mail.qq.com)")
    print("2. 设置 → 账户 → POP3/IMAP/SMTP服务")
    print("3. 开启 IMAP/SMTP 服务")
    print("4. 生成授权码（16位字符）")
    print("5. 将授权码作为密码使用\n")
    
    # 获取用户输入
    print("请输入您的QQ邮箱信息:")
    qq_email = input("QQ邮箱地址: ").strip()
    if not qq_email:
        print("❌ 请输入QQ邮箱地址")
        return
    
    auth_code = input("QQ邮箱授权码（16位）: ").strip()
    if not auth_code:
        print("❌ 请输入授权码")
        return
    
    # 创建新的配置文件
    config = configparser.ConfigParser()
    config['EMAIL'] = {
        'smtp_server': 'smtp.qq.com',
        'smtp_port': '587',
        'username': qq_email,
        'password': auth_code,
        'sender_name': 'MT4数据处理系统'
    }
    
    # 保存配置
    with open('email_config_qq.ini', 'w', encoding='utf-8') as f:
        config.write(f)
    
    print(f"\n✅ QQ邮箱配置已保存到: email_config_qq.ini")
    
    # 测试连接
    print("\n🔄 测试QQ邮箱连接...")
    test_success = test_qq_connection(qq_email, auth_code)
    
    if test_success:
        # 询问是否替换主配置
        replace = input("\n✅ QQ邮箱测试成功！是否替换为主配置？(y/n): ").strip().lower()
        if replace == 'y':
            # 备份原配置
            import shutil
            import os
            if os.path.exists('email_config.ini'):
                shutil.copy('email_config.ini', 'email_config_backup.ini')
                print("📋 原配置已备份为: email_config_backup.ini")
            
            # 替换主配置
            shutil.copy('email_config_qq.ini', 'email_config.ini')
            print("✅ QQ邮箱配置已设为主配置")
            
            # 发送测试邮件
            send_test = input("\n📧 是否发送测试邮件？(y/n): ").strip().lower()
            if send_test == 'y':
                send_qq_test_email(qq_email, auth_code)

def test_qq_connection(qq_email, auth_code):
    """
    测试QQ邮箱连接
    """
    try:
        server = smtplib.SMTP('smtp.qq.com', 587, timeout=30)
        server.starttls()
        server.login(qq_email, auth_code)
        server.quit()
        print("✅ QQ邮箱连接测试成功！")
        return True
    except Exception as e:
        print(f"❌ QQ邮箱连接失败: {str(e)}")
        print("\n💡 请检查:")
        print("   - QQ邮箱地址是否正确")
        print("   - 授权码是否正确（16位字符）")
        print("   - 是否已开启IMAP/SMTP服务")
        return False

def send_qq_test_email(qq_email, auth_code):
    """
    使用QQ邮箱发送测试邮件
    """
    try:
        recipient = input("请输入收件人邮箱: ").strip()
        if not recipient:
            recipient = qq_email  # 默认发给自己
        
        # 创建测试邮件
        msg = MIMEText(f"""
🎉 QQ邮箱配置成功！

发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
发件人: {qq_email}
收件人: {recipient}

这是来自MT4数据处理系统的测试邮件。
如果您收到此邮件，说明QQ邮箱配置完全正确！

下一步可以：
✅ 发送带附件的MT4数据报告
✅ 自动处理和发送MT4数据

---
MT4数据处理系统
        """, 'plain', 'utf-8')
        
        msg['From'] = f"MT4数据处理系统 <{qq_email}>"
        msg['To'] = recipient
        msg['Subject'] = f"QQ邮箱配置测试成功 - {datetime.now().strftime('%H:%M:%S')}"
        
        # 发送邮件
        server = smtplib.SMTP('smtp.qq.com', 587, timeout=30)
        server.starttls()
        server.login(qq_email, auth_code)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ 测试邮件已发送到: {recipient}")
        print("📧 请检查邮箱查收（可能需要几分钟）")
        
    except Exception as e:
        print(f"❌ 发送测试邮件失败: {str(e)}")

if __name__ == "__main__":
    setup_qq_email()