#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
超简单扩展脚本
5分钟创建新的表格处理器
"""

import os
import shutil
import configparser

def create_new_processor():
    """创建新的表格处理器"""
    print("🚀 === 5分钟创建新表格处理器 ===\n")
    
    # 1. 获取用户输入
    name = input("📝 请输入新处理器名称 (如: stock_processor): ").strip()
    if not name:
        name = "new_processor"
    
    pattern = input("📁 请输入文件匹配字符串 (如: STOCK_DATA): ").strip()
    if not pattern:
        pattern = "NEW_TABLE"
    
    email = input("📧 请输入收件人邮箱 (如: user@email.com): ").strip()
    if not email:
        email = "test@example.com"
    
    # 2. 创建新目录
    new_dir = f"d:\\qoder\\{name}"
    if os.path.exists(new_dir):
        print(f"⚠️ 目录已存在: {new_dir}")
        return
    
    print(f"📁 创建目录: {new_dir}")
    shutil.copytree(".", new_dir, ignore=shutil.ignore_patterns(
        '*.xlsx', '*.jpg', '*.png', '__pycache__', '.git*'
    ))
    
    # 3. 修改配置文件
    config_file = os.path.join(new_dir, "simple_config.ini")
    if os.path.exists(config_file):
        config = configparser.ConfigParser()
        config.read(config_file)
        
        # 更新配置
        config['FILES']['pattern'] = pattern
        config['EMAIL']['recipients'] = email
        
        with open(config_file, 'w') as f:
            config.write(f)
        
        print(f"✅ 配置文件已更新: {config_file}")
    
    # 4. 创建启动脚本
    start_script = os.path.join(new_dir, f"start_{name}.py")
    with open(start_script, 'w', encoding='utf-8') as f:
        f.write(f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
{name} 启动脚本
"""

import os
import sys

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(__file__))

# 导入并运行处理器
from auto_email_config import run_auto_email_system

if __name__ == "__main__":
    print(f"🚀 启动 {name} 处理器")
    run_auto_email_system()
''')
    
    print(f"✅ 启动脚本已创建: {start_script}")
    
    # 5. 显示使用说明
    print(f"\n🎉 === 创建完成！ ===")
    print(f"📁 新处理器位置: {new_dir}")
    print(f"⚙️ 配置文件: {config_file}")
    print(f"🚀 启动命令: python {start_script}")
    print(f"\n💡 下次使用:")
    print(f"   1. 进入目录: cd {new_dir}")
    print(f"   2. 运行处理: python start_{name}.py")
    
    print(f"\n📝 如需修改配置，编辑: {config_file}")

if __name__ == "__main__":
    create_new_processor()