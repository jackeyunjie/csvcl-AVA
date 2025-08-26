#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片格式配置脚本
允许用户选择JPG或PNG格式保存截图
"""

import configparser
import os

def create_image_config():
    """
    创建图片格式配置文件
    """
    config_file = "image_config.ini"
    
    print("🖼️ === 图片格式配置 ===\n")
    
    print("📋 支持的图片格式:")
    print("1. JPG格式")
    print("   ✅ 文件更小（约90KB）")
    print("   ✅ 邮件发送更快")
    print("   ✅ 节省存储空间")
    print("   ✅ 质量可调（默认95%）")
    print()
    print("2. PNG格式")
    print("   ✅ 无损压缩")
    print("   ✅ 支持透明背景")
    print("   ✅ 更清晰（但文件较大）")
    print("   ⚠️  文件较大（约180KB）")
    print()
    
    # 询问用户选择
    while True:
        choice = input("请选择图片格式 (1=JPG, 2=PNG): ").strip()
        
        if choice == "1":
            image_format = "JPG"
            quality = input("请输入JPG质量（1-100，默认95）: ").strip()
            try:
                quality = int(quality) if quality else 95
                if not 1 <= quality <= 100:
                    quality = 95
            except ValueError:
                quality = 95
            break
        elif choice == "2":
            image_format = "PNG"
            quality = 100  # PNG质量固定为100
            break
        else:
            print("❌ 无效选择，请输入1或2")
    
    # 创建配置文件
    config = configparser.ConfigParser()
    config['IMAGE'] = {
        'format': image_format,
        'quality': str(quality),
        'width': '1080',
        'height': '1025',
        'include_headers': 'true'
    }
    
    with open(config_file, 'w', encoding='utf-8') as f:
        config.write(f)
    
    print(f"\n✅ 配置已保存到: {config_file}")
    print(f"📐 图片格式: {image_format}")
    print(f"🎨 图片质量: {quality}%")
    print(f"📏 图片尺寸: 1080 x 1025 像素")
    
    return config_file

def load_image_config():
    """
    加载图片格式配置
    """
    config_file = "image_config.ini"
    
    if not os.path.exists(config_file):
        # 默认配置
        return {
            'format': 'JPG',
            'quality': 95,
            'width': 1080,
            'height': 1025,
            'include_headers': True
        }
    
    try:
        config = configparser.ConfigParser()
        config.read(config_file, encoding='utf-8')
        
        return {
            'format': config.get('IMAGE', 'format', fallback='JPG'),
            'quality': config.getint('IMAGE', 'quality', fallback=95),
            'width': config.getint('IMAGE', 'width', fallback=1080),
            'height': config.getint('IMAGE', 'height', fallback=1025),
            'include_headers': config.getboolean('IMAGE', 'include_headers', fallback=True)
        }
    except Exception as e:
        print(f"⚠️ 读取配置失败: {e}")
        return {
            'format': 'JPG',
            'quality': 95,
            'width': 1080,
            'height': 1025,
            'include_headers': True
        }

def show_current_config():
    """
    显示当前配置
    """
    config = load_image_config()
    
    print("🖼️ === 当前图片配置 ===")
    print(f"📐 格式: {config['format']}")
    print(f"🎨 质量: {config['quality']}%")
    print(f"📏 尺寸: {config['width']} x {config['height']} 像素")
    print(f"🏷️ 包含边框: {'是' if config['include_headers'] else '否'}")

def compare_formats():
    """
    对比两种格式的特点
    """
    print("📊 === 格式对比 ===")
    print()
    
    print("📈 文件大小对比（A1:M40截图）:")
    print("   JPG (95%质量): ~90KB")
    print("   PNG (无损):   ~180KB")
    print("   压缩比: JPG比PNG小约50%")
    print()
    
    print("⚡ 邮件发送速度:")
    print("   JPG: 更快（文件小）")
    print("   PNG: 较慢（文件大）")
    print()
    
    print("🎯 适用场景:")
    print("   JPG: 邮件发送、日常报告、存储空间有限")
    print("   PNG: 高质量存档、需要透明背景、图像编辑")
    print()
    
    print("💡 建议:")
    print("   📧 邮件发送: 推荐JPG格式")
    print("   💾 长期存档: 推荐PNG格式")

if __name__ == "__main__":
    print("请选择操作:")
    print("1. 配置图片格式")
    print("2. 查看当前配置")
    print("3. 格式对比说明")
    
    choice = input("\n请选择 (1/2/3): ").strip()
    
    if choice == "1":
        create_image_config()
    elif choice == "2":
        show_current_config()
    elif choice == "3":
        compare_formats()
    else:
        print("❌ 无效选择")