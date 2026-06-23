#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证MT4数据处理和邮件发送 - 实际测试脚本
"""

import os
import sys
import time
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from process_real_mt4_data import RealMT4DataProcessor

def test_with_real_file(file_path=None):
    """使用实际MT4文件进行测试"""
    print("=== MT4数据处理和邮件发送测试 ===")
    
    # 如果未提供文件路径，则使用最新的CSV文件
    if not file_path:
        # 查找目录中最新的KVBt_@_D1 CSV文件
        csv_files = [f for f in os.listdir('.') if f.endswith('.csv') and 'KVBt_@_D1' in f]
        if not csv_files:
            print("❌ 未找到KVBt_@_D1 CSV文件")
            return False
        
        # 按修改时间排序，获取最新的文件
        csv_files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
        file_path = csv_files[0]
        print(f"📊 使用最新的CSV文件: {file_path}")
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return False
    
    # 创建MT4数据处理器实例（启用邮件发送功能）
    print(f"🔄 创建MT4数据处理器...")
    processor = RealMT4DataProcessor(
        mt4_path=".",  # 使用当前目录
        target_string="KVBt_@_D1",
        time_limit_minutes=60*24*7,  # 设置足够大的时间范围，以确保找到文件
        enable_email=True,  # 启用邮件发送
        recipients=["447372703@qq.com"]  # 设置收件人
    )
    
    # 直接处理指定的文件
    print(f"🔄 处理文件: {file_path}")
    excel_path, image_path, data_changes = processor.process_real_csv_data(file_path)
    
    if not excel_path or not image_path:
        print("❌ 文件处理失败")
        return False
    
    # 发送邮件报告
    print(f"\n📧 发送邮件报告...")
    success = processor.email_sender.send_mt4_report(
        excel_files=[excel_path],
        image_files=[image_path],
        recipients=processor.recipients,
        subject=f"MT4数据处理报告 - 测试 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        data_changes=data_changes
    )
    
    if success:
        print("✅ 测试完成")
        print("请检查邮箱收件箱，确认以下几点:")
        print("1. 邮件是否成功接收")
        print("2. Excel附件是否可以正常打开")
        print("3. Excel文件中的颜色标记是否正确显示")
        print("4. 邮件中的图片是否正确显示")
        return True
    else:
        print("❌ 邮件发送失败")
        return False

def main():
    """主函数"""
    # 查找参数中是否指定了文件路径
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        test_with_real_file(file_path)
    else:
        test_with_real_file()

if __name__ == "__main__":
    main()