#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用数据处理系统入口
支持通过配置文件驱动不同的处理逻辑
"""

import argparse
import os
import sys
from datetime import datetime

# 添加core目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))

from config_manager import ConfigManager

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='通用数据处理系统')
    parser.add_argument('--config', '-c', 
                       default='configs/mt4_config.yaml',
                       help='配置文件路径 (默认: configs/mt4_config.yaml)')
    parser.add_argument('--list-configs', '-l', 
                       action='store_true',
                       help='列出所有可用的配置文件')
    parser.add_argument('--validate', '-v',
                       action='store_true', 
                       help='仅验证配置文件')
    parser.add_argument('--dry-run', '-d',
                       action='store_true',
                       help='干运行模式（不执行实际操作）')
    
    args = parser.parse_args()
    
    # 列出配置文件
    if args.list_configs:
        list_available_configs()
        return
    
    # 检查配置文件是否存在
    if not os.path.exists(args.config):
        print(f"❌ 配置文件不存在: {args.config}")
        print("\n💡 可用的配置文件:")
        list_available_configs()
        return
    
    try:
        # 加载配置
        config_manager = ConfigManager(args.config)
        
        # 验证配置
        if not config_manager.validate_config():
            print("❌ 配置文件验证失败")
            return
        
        if args.validate:
            print("✅ 配置文件验证通过")
            config_manager.print_config_summary()
            return
        
        # 打印配置摘要
        config_manager.print_config_summary()
        
        if args.dry_run:
            print("🔍 === 干运行模式 ===")
            print("以下是将要执行的操作：")
            simulate_processing(config_manager)
            return
        
        # 执行实际处理
        print(f"\n🚀 === 开始处理 ===")
        run_processing(config_manager)
        
    except Exception as e:
        print(f"❌ 程序执行失败: {e}")
        import traceback
        traceback.print_exc()

def list_available_configs():
    """列出所有可用的配置文件"""
    configs_dir = "configs"
    if not os.path.exists(configs_dir):
        print(f"❌ 配置目录不存在: {configs_dir}")
        return
    
    config_files = [f for f in os.listdir(configs_dir) if f.endswith('.yaml')]
    
    if not config_files:
        print(f"❌ 在 {configs_dir} 目录中没有找到配置文件")
        return
    
    print(f"\n📋 可用的配置文件:")
    for i, config_file in enumerate(config_files, 1):
        config_path = os.path.join(configs_dir, config_file)
        try:
            # 尝试读取配置文件的基本信息
            temp_manager = ConfigManager(config_path)
            name = temp_manager.get('name', '未知')
            description = temp_manager.get('description', '无描述')
            print(f"   {i}. {config_file}")
            print(f"      名称: {name}")
            print(f"      描述: {description}")
            print()
        except:
            print(f"   {i}. {config_file} (配置文件格式错误)")

def simulate_processing(config_manager: ConfigManager):
    """模拟处理过程（干运行）"""
    print(f"1. 📁 搜索文件:")
    search_paths = config_manager.get_search_paths()
    pattern = config_manager.get_file_pattern()
    time_limit = config_manager.get_time_limit_minutes()
    
    for path in search_paths:
        print(f"   - 在 {path} 中搜索匹配 '{pattern}' 的文件")
    print(f"   - 时间限制: {time_limit} 分钟内的文件")
    
    print(f"\n2. 🎨 颜色标记:")
    target_range = config_manager.get_target_range()
    color_rules = config_manager.get_color_rules()
    print(f"   - 处理区域: {target_range}")
    print(f"   - 颜色规则数量: {len(color_rules)}")
    
    print(f"\n3. 📊 数据分析:")
    analyzer_type = config_manager.get_analyzer_type()
    print(f"   - 分析器类型: {analyzer_type}")
    
    print(f"\n4. 📸 生成截图:")
    screenshot_range = config_manager.get_screenshot_range()
    image_config = config_manager.get_image_config()
    print(f"   - 截图区域: {screenshot_range}")
    print(f"   - 图片格式: {image_config.get('format', 'jpg')}")
    
    if config_manager.is_email_enabled():
        print(f"\n5. 📧 发送邮件:")
        recipients = config_manager.get_email_recipients()
        start_time, end_time = config_manager.get_send_time_range()
        print(f"   - 收件人数量: {len(recipients)}")
        print(f"   - 发送时间: {start_time} - {end_time}")
    else:
        print(f"\n5. 📧 邮件发送: 已禁用")

def run_processing(config_manager: ConfigManager):
    """运行实际的处理逻辑"""
    try:
        # 这里需要导入并使用通用处理器
        # 由于现在还没有创建，我们先模拟
        print("🔄 正在导入通用处理器...")
        
        # TODO: 实际导入和使用通用处理器
        # from core.universal_processor import UniversalProcessor
        # processor = UniversalProcessor(config_manager)
        # processor.run()
        
        print("⚠️  通用处理器尚未实现，请稍后...")
        print("💡 您可以使用以下命令继续使用现有的MT4处理器:")
        print("   python auto_email_config.py")
        
    except Exception as e:
        print(f"❌ 处理过程中出错: {e}")
        raise

def create_sample_usage():
    """创建使用示例"""
    print(f"\n📖 === 使用示例 ===")
    print(f"# 使用MT4配置处理数据")
    print(f"python universal_main.py --config configs/mt4_config.yaml")
    print(f"")
    print(f"# 使用新表格配置处理数据") 
    print(f"python universal_main.py --config configs/new_table_config.yaml")
    print(f"")
    print(f"# 验证配置文件")
    print(f"python universal_main.py --config configs/mt4_config.yaml --validate")
    print(f"")
    print(f"# 干运行模式")
    print(f"python universal_main.py --config configs/mt4_config.yaml --dry-run")
    print(f"")
    print(f"# 列出所有配置")
    print(f"python universal_main.py --list-configs")

if __name__ == "__main__":
    print("🎯 通用数据处理系统")
    print("=" * 50)
    
    if len(sys.argv) == 1:
        # 没有参数时显示帮助和示例
        print("请指定配置文件或使用 --help 查看帮助")
        create_sample_usage()
    else:
        main()