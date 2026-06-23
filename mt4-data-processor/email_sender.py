#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件发送功能模块
用于发送MT4数据处理结果和截图
"""

import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
import configparser

class EmailSender:
    def __init__(self, config_file=None):
        """
        初始化邮件发送器
        
        Args:
            config_file (str): 配置文件路径
        """
        self.config_file = config_file or "email_config.ini"
        self.smtp_server = None
        self.smtp_port = None
        self.username = None
        self.password = None
        self.sender_name = None
        
        # 尝试加载配置
        self.load_config()
    
    def load_config(self):
        """
        加载邮件配置
        """
        try:
            if os.path.exists(self.config_file):
                config = configparser.ConfigParser()
                config.read(self.config_file, encoding='utf-8')
                
                self.smtp_server = config.get('EMAIL', 'smtp_server', fallback='smtp.qq.com')
                self.smtp_port = config.getint('EMAIL', 'smtp_port', fallback=587)
                self.username = config.get('EMAIL', 'username', fallback='')
                self.password = config.get('EMAIL', 'password', fallback='')
                self.sender_name = config.get('EMAIL', 'sender_name', fallback='MT4数据处理系统')
                
                print(f"✅ 已加载邮件配置: {self.config_file}")
            else:
                print(f"⚠️  邮件配置文件不存在: {self.config_file}")
                self.create_default_config()
                
        except Exception as e:
            print(f"❌ 加载邮件配置失败: {str(e)}")
            self.create_default_config()
    
    def create_default_config(self):
        """
        创建默认配置文件
        """
        try:
            config = configparser.ConfigParser()
            config['EMAIL'] = {
                'smtp_server': 'smtp.qq.com',
                'smtp_port': '587',
                'username': 'your_email@qq.com',
                'password': 'your_app_password',
                'sender_name': 'MT4数据处理系统'
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                config.write(f)
            
            print(f"📋 已创建默认配置文件: {self.config_file}")
            print("⚠️  请编辑配置文件，填入您的邮箱信息")
            
        except Exception as e:
            print(f"❌ 创建配置文件失败: {str(e)}")
    
    def send_mt4_report(self, excel_files=None, image_files=None, recipients=None, subject=None, data_changes=None):
        """
        发送MT4数据处理报告
        
        Args:
            excel_files (list): Excel文件路径列表
            image_files (list): 图片文件路径列表
            recipients (list): 收件人邮箱列表
            subject (str): 邮件主题
        """
        try:
            print(f"\n📧 === 准备发送MT4数据报告 ===")
            
            # 检查配置
            if not self.username or not self.password:
                print("❌ 邮箱配置不完整，请检查配置文件")
                return False
            
            if not recipients:
                print("❌ 请提供收件人邮箱地址")
                return False
            
            # 创建邮件
            msg = MIMEMultipart('related')
            msg['From'] = self.username
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject or f"MT4数据文件 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            # 创建HTML邮件正文，包含嵌入的图片
            html_body = self.create_html_body_with_images(excel_files, image_files, data_changes)
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))
            
            # 添加Excel文件附件
            if excel_files:
                for excel_file in excel_files:
                    if os.path.exists(excel_file):
                        self.attach_file(msg, excel_file)
                        print(f"📊 已添加Excel附件: {os.path.basename(excel_file)}")
            
            # 将图片嵌入邮件正文而不是作为附件
            if image_files:
                for i, image_file in enumerate(image_files):
                    if os.path.exists(image_file):
                        self.embed_image(msg, image_file, f"image{i+1}")
                        print(f"🖼️  已嵌入图片: {os.path.basename(image_file)}")
            
            # 发送邮件 - 添加重试机制
            for attempt in range(3):  # 重试3次
                try:
                    print(f"🔄 正在连接邮件服务器: {self.smtp_server}:{self.smtp_port} (第{attempt+1}次尝试)")
                    
                    if self.smtp_port == 465:
                        # SSL连接
                        server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=30)
                    else:
                        # TLS连接
                        server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30)
                        server.starttls()
                    
                    print(f"✅ 服务器连接成功")
                    
                    # 登录
                    server.login(self.username, self.password)
                    print(f"✅ 邮箱登录成功: {self.username}")
                    
                    # 发送给所有收件人（一次性发送）
                    # 将所有收件人放在To字段中
                    text = msg.as_string()
                    server.sendmail(self.username, recipients, text)
                    print(f"✅ 邮件已发送给: {', '.join(recipients)}")
                    
                    server.quit()
                    print(f"🎉 MT4数据报告发送完成！")
                    return True
                    
                except smtplib.SMTPException as e:
                    print(f"❌ 第{attempt+1}次尝试失败: {str(e)}")
                    if attempt < 2:  # 不是最后一次尝试
                        print(f"🔄 5秒后重试...")
                        import time
                        time.sleep(5)
                    continue
                except Exception as e:
                    print(f"❌ 第{attempt+1}次尝试失败: {str(e)}")
                    if attempt < 2:
                        print(f"🔄 5秒后重试...")
                        import time
                        time.sleep(5)
                    continue
            
            # 所有尝试都失败
            print(f"❌ 所有尝试都失败")
            print("💡 常见问题排查:")
            print("   - 检查网络连接")
            print("   - 确认邮箱用户名和密码正确")
            print("   - 如果使用QQ邮箱，请使用授权码而不是登录密码")
            print("   - 检查SMTP服务器设置")
            print("   - 尝试减少附件数量或大小")
            return False
            
        except Exception as e:
            print(f"❌ 发送邮件失败: {str(e)}")
            print("💡 常见问题排查:")
            print("   - 检查网络连接")
            print("   - 确认邮箱用户名和密码正确")
            print("   - 如果使用QQ邮箱，请使用授权码而不是登录密码")
            print("   - 检查SMTP服务器设置")
            return False
    
    def attach_file(self, msg, file_path):
        """
        添加文件附件（改进版，修复文件名编码问题）
        """
        try:
            import mimetypes
            from email.header import Header
            
            filename = os.path.basename(file_path)
            # 使用ASCII兼容的文件名编码
            safe_filename = filename.encode('ascii', 'ignore').decode('ascii')
            if not safe_filename:
                # 如果ASCII编码后为空，使用简化文件名
                import time
                safe_filename = f"MT4_file_{int(time.time())}.xlsx"
            
            # 根据文件扩展名自动检测MIME类型
            if filename.endswith('.xlsx'):
                main_type = 'application'
                sub_type = 'vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            elif filename.endswith('.xls'):
                main_type = 'application'
                sub_type = 'vnd.ms-excel'
            elif filename.endswith('.csv'):
                main_type = 'text'
                sub_type = 'csv'
            else:
                main_type = 'application'
                sub_type = 'octet-stream'
            
            with open(file_path, 'rb') as f:
                part = MIMEBase(main_type, sub_type)
                part.set_payload(f.read())
                encoders.encode_base64(part)
                
                # 使用RFC2047编码的文件名
                encoded_filename = Header(filename, 'utf-8').encode()
                part.add_header(
                    'Content-Disposition',
                    f'attachment',
                    filename=('utf-8', '', filename)
                )
                
                # 添加Content-Type头
                part.add_header('Content-Type', f'{main_type}/{sub_type}', name=('utf-8', '', filename))
                
                msg.attach(part)
                
        except Exception as e:
            print(f"❌ 添加附件失败 {file_path}: {str(e)}")
    
    def attach_image(self, msg, image_path):
        """
        添加图片附件（改进版，修复文件类型问题）
        """
        try:
            filename = os.path.basename(image_path)
            
            # 根据文件扩展名确定图片类型
            if filename.lower().endswith('.jpg') or filename.lower().endswith('.jpeg'):
                image_type = 'jpeg'
            elif filename.lower().endswith('.png'):
                image_type = 'png'
            elif filename.lower().endswith('.gif'):
                image_type = 'gif'
            elif filename.lower().endswith('.bmp'):
                image_type = 'bmp'
            else:
                image_type = 'jpeg'  # 默认使用jpeg
            
            with open(image_path, 'rb') as f:
                img_data = f.read()
                image = MIMEImage(img_data, _subtype=image_type)
                
                # 使用正确的文件名格式
                image.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{filename}"'
                )
                
                # 添加Content-Type头
                image.add_header('Content-Type', f'image/{image_type}; name="{filename}"')
                
                msg.attach(image)
                
        except Exception as e:
            print(f"❌ 添加图片失败 {image_path}: {str(e)}")
    
    def create_html_body_with_images(self, excel_files, image_files, data_changes=None):
        """
        创建包含嵌入图片和数据变化分析的HTML邮件正文
        """
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        html = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background-color: #4CAF50; color: white; padding: 15px; text-align: center; }}
                .content {{ padding: 20px; }}
                .file-list {{ background-color: #f9f9f9; padding: 15px; margin: 10px 0; }}
                .changes-section {{ background-color: #e8f4fd; padding: 15px; margin: 15px 0; border-left: 4px solid #2196F3; }}
                .change-item {{ background-color: #ffffff; padding: 10px; margin: 5px 0; border-radius: 3px; border: 1px solid #ddd; }}
                .image-container {{ margin: 20px 0; text-align: center; }}
                .image-container img {{ max-width: 100%; height: auto; border: 1px solid #ddd; }}
                .footer {{ background-color: #f5f5f5; padding: 10px; text-align: center; font-size: 12px; }}
                .highlight {{ font-weight: bold; color: #d32f2f; }}
                .symbol {{ font-weight: bold; color: #1976d2; }}
                .value-change {{ font-weight: bold; }}
                .positive {{ color: #388e3c; }}
                .negative {{ color: #d32f2f; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>📊 MT4数据文件</h2>
                <p>{current_time}</p>
            </div>
            
            <div class="content">
        """
        
        # 添加数据变化分析结果
        if data_changes and len(data_changes) > 0:
            html += '''
            <div class="changes-section">
                <h3>📊 重要数据变化分析</h3>
                <p>以下是今日相对于昨日变成<strong>2、6、-2、-6</strong>的重要变化：</p>
            '''
            
            for change in data_changes:
                symbol = change['symbol']
                column = change['column']
                today_date = change['today_date']
                from_value = change['from_value']
                to_value = change['to_value']
                
                # 判断变化类型
                value_class = "positive" if to_value > 0 else "negative"
                
                # 格式化列名
                column_name_map = {
                    'MN1': '月线(MN1)',
                    'W1': '周线(W1)', 
                    'D1': '日线(D1)'
                }
                column_display = column_name_map.get(column, column)
                
                html += f'''
                <div class="change-item">
                    <span class="symbol">💹 {symbol}</span> - 
                    <span class="highlight">{column_display}</span> 列：
                    <span class="value-change">{from_value} → <span class="{value_class}">{to_value}</span></span>
                    <br><small>📅 日期: {today_date}</small>
                </div>
                '''
            
            html += '</div>'
        else:
            html += '''
            <div class="changes-section">
                <h3>📊 数据变化分析</h3>
                <p>✅ 今日未发现重要数值变化（2、6、-2、-6）</p>
            </div>
            '''
        
        if excel_files:
            html += '<div class="file-list"><h3>📊 Excel文件:</h3><ul>'
            for file_path in excel_files:
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path) / 1024
                    filename = os.path.basename(file_path)
                    html += f'<li>📊 {filename} ({file_size:.1f}KB)</li>'
            html += '</ul></div>'
        
        if image_files:
            html += '<h3>🖼️ 数据截图:</h3>'
            for i, file_path in enumerate(image_files):
                if os.path.exists(file_path):
                    filename = os.path.basename(file_path)
                    html += f'''
                    <div class="image-container">
                        <h4>{filename}</h4>
                        <img src="cid:image{i+1}" alt="{filename}">
                    </div>
                    '''
        
        html += """
            </div>
            
            <div class="footer">
                <p>🤖 此邮件由MT4数据处理系统自动发送</p>
            </div>
        </body>
        </html>
        """
        
        return html
        
    def embed_image(self, msg, image_path, cid):
        """
        将图片嵌入邮件正文
        """
        try:
            filename = os.path.basename(image_path)
            
            with open(image_path, 'rb') as f:
                img_data = f.read()
                
                # 根据文件扩展名确定图片类型
                if filename.lower().endswith('.jpg') or filename.lower().endswith('.jpeg'):
                    image_type = 'jpeg'
                elif filename.lower().endswith('.png'):
                    image_type = 'png'
                else:
                    image_type = 'jpeg'
                
                image = MIMEImage(img_data, _subtype=image_type)
                image.add_header('Content-ID', f'<{cid}>')
                image.add_header('Content-Disposition', 'inline', filename=filename)
                
                msg.attach(image)
                
        except Exception as e:
            print(f"❌ 嵌入图片失败 {image_path}: {str(e)}")

def main():
    """
    测试邮件发送功能
    """
    print("📧 邮件发送功能测试")
    
    sender = EmailSender()
    
    # 示例：发送测试邮件
    test_recipients = ["test@example.com"]  # 请替换为实际邮箱
    
    # 查找最新的MT4文件
    import glob
    excel_files = glob.glob("*MT4_colored.xlsx")[:2]  # 最多发送2个Excel文件
    image_files = glob.glob("*MT4_screenshot.png")[:2]  # 最多发送2个截图
    
    if excel_files or image_files:
        sender.send_mt4_report(
            excel_files=excel_files,
            image_files=image_files,
            recipients=test_recipients,
            subject="MT4数据处理测试报告"
        )
    else:
        print("❌ 未找到MT4处理文件")

if __name__ == "__main__":
    main()