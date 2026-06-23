#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
原始版本MT4数据处理和邮件发送测试
完全按照Gitee原始版本的方式工作
"""

import os
import sys
import glob
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from process_real_mt4_data import RealMT4DataProcessor

def find_latest_csv_file():
    """查找最新的KVBt_@_D1 CSV文件"""
    csv_files = [f for f in os.listdir('.') if f.endswith('.csv') and 'KVBt_@_D1' in f]
    if not csv_files:
        print("❌ 未找到KVBt_@_D1 CSV文件")
        return None
        
    # 按修改时间排序
    csv_files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
    
    # 返回最新的文件
    latest_file = csv_files[0]
    print(f"📊 找到最新的CSV文件: {latest_file}")
    print(f"   创建时间: {datetime.fromtimestamp(os.path.getmtime(latest_file)).strftime('%Y-%m-%d %H:%M:%S')}")
    return latest_file

def test_original_version():
    """使用原始版本处理MT4数据并发送邮件"""
    print("=== 原始版本MT4数据处理和邮件发送测试 ===")
    
    # 查找最新的CSV文件
    csv_file = find_latest_csv_file()
    if not csv_file:
        print("❌ 无法继续测试，请确保有KVBt_@_D1 CSV文件")
        return False
    
    # 创建MT4数据处理器（启用邮件发送功能）
    print(f"🔄 创建MT4数据处理器...")
    processor = RealMT4DataProcessor(
        mt4_path=".",  # 使用当前目录
        target_string="KVBt_@_D1",
        time_limit_minutes=60*24*7,  # 设置足够大的时间范围，以确保找到文件
        enable_email=True,  # 启用邮件发送
        recipients=["447372703@qq.com", "1300893414@qq.com"]  # 设置收件人
    )
    
    # 处理CSV文件
    print(f"🔄 处理CSV文件: {csv_file}")
    excel_path, image_path, data_changes = processor.process_real_csv_data(csv_file)
    
    if not excel_path or not image_path:
        print("❌ CSV文件处理失败")
        return False
    
    # 显示处理结果
    print(f"\n📊 处理结果:")
    print(f"   Excel文件: {os.path.basename(excel_path)}")
    print(f"   图片文件: {os.path.basename(image_path)}")
    if data_changes:
        print(f"   数据变化: {len(data_changes)} 个")
    
    # 发送邮件报告
    print(f"\n📧 发送邮件报告...")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    success = processor.email_sender.send_mt4_report(
        excel_files=[excel_path],
        image_files=[image_path],
        recipients=processor.recipients,
        subject=f"MT4数据处理报告 - 原始版本测试 {timestamp}",
        data_changes=data_changes
    )
    
    if success:
        print("✅ 邮件发送成功")
        print("请检查收件箱，验证邮件内容和附件")
        return True
    else:
        print("❌ 邮件发送失败")
        return False

if __name__ == "__main__":
    test_original_version()