#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel文件打开助手
提供多种方式打开生成的Excel文件
"""

import os
import subprocess
import sys

def open_excel_file():
    """
    尝试用多种方式打开Excel文件
    """
    # 查找最新的colored.xlsx文件
    current_dir = os.path.dirname(__file__)
    xlsx_files = [f for f in os.listdir(current_dir) if f.endswith('_colored.xlsx') and not f.startswith('~$')]
    
    if not xlsx_files:
        print("❌ 未找到任何Excel文件")
        return
    
    # 按修改时间排序，获取最新文件
    xlsx_files.sort(key=lambda x: os.path.getmtime(os.path.join(current_dir, x)), reverse=True)
    latest_file = xlsx_files[0]
    file_path = os.path.join(current_dir, latest_file)
    
    print(f"📁 准备打开文件: {latest_file}")
    print(f"📍 文件路径: {file_path}")
    
    # 方法1: 使用默认程序打开
    try:
        print("\n🔄 方法1: 使用系统默认程序打开...")
        os.startfile(file_path)
        print("✅ 文件已发送到系统默认程序")
        return True
    except Exception as e:
        print(f"❌ 方法1失败: {e}")
    
    # 方法2: 使用start命令
    try:
        print("\n🔄 方法2: 使用start命令...")
        subprocess.run(['start', '', file_path], shell=True, check=True)
        print("✅ 文件已通过start命令打开")
        return True
    except Exception as e:
        print(f"❌ 方法2失败: {e}")
    
    # 方法3: 直接调用Excel
    excel_paths = [
        r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
        r"C:\Program Files (x86)\Microsoft Office\root\Office16\EXCEL.EXE",
        r"C:\Program Files\Microsoft Office\Office16\EXCEL.EXE",
        r"C:\Program Files (x86)\Microsoft Office\Office16\EXCEL.EXE",
    ]
    
    for excel_path in excel_paths:
        if os.path.exists(excel_path):
            try:
                print(f"\n🔄 方法3: 直接调用Excel ({excel_path})...")
                subprocess.Popen([excel_path, file_path])
                print("✅ Excel已启动")
                return True
            except Exception as e:
                print(f"❌ 调用Excel失败: {e}")
    
    print("\n❌ 所有方法都失败了")
    print("\n💡 手动解决方案:")
    print(f"1. 打开文件资源管理器")
    print(f"2. 导航到: {current_dir}")
    print(f"3. 双击文件: {latest_file}")
    print(f"\n或者复制此路径到资源管理器地址栏:")
    print(f"{file_path}")
    
    return False

def list_available_files():
    """
    列出所有可用的Excel文件
    """
    current_dir = os.path.dirname(__file__)
    xlsx_files = [f for f in os.listdir(current_dir) if f.endswith('_colored.xlsx') and not f.startswith('~$')]
    
    if not xlsx_files:
        print("❌ 未找到任何Excel文件")
        return
    
    print(f"\n📂 找到 {len(xlsx_files)} 个Excel文件:")
    for i, file_name in enumerate(xlsx_files, 1):
        file_path = os.path.join(current_dir, file_name)
        file_size = os.path.getsize(file_path)
        mod_time = os.path.getmtime(file_path)
        import datetime
        mod_time_str = datetime.datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')
        print(f"  {i}. {file_name}")
        print(f"     大小: {file_size} 字节")
        print(f"     修改时间: {mod_time_str}")
        print(f"     路径: {file_path}")
        print()

def main():
    """
    主函数
    """
    print("=== Excel文件打开助手 ===")
    
    list_available_files()
    
    while True:
        print("\n选择操作:")
        print("1. 打开最新的Excel文件")
        print("2. 列出所有Excel文件")
        print("3. 退出")
        
        choice = input("\n请输入选择 (1-3): ").strip()
        
        if choice == '1':
            open_excel_file()
        elif choice == '2':
            list_available_files()
        elif choice == '3':
            print("👋 再见!")
            break
        else:
            print("❌ 无效选择，请重试")

if __name__ == "__main__":
    main()