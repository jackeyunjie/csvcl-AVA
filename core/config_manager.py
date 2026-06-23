#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理器
负责加载和解析YAML配置文件
"""

import yaml
import os
from datetime import time
from typing import Dict, List, Any, Optional

class ConfigManager:
    """配置管理器类"""
    
    def __init__(self, config_path: str):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config = {}
        self.load_config()
    
    def load_config(self) -> None:
        """加载配置文件"""
        try:
            if not os.path.exists(self.config_path):
                raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            
            print(f"✅ 配置文件加载成功: {self.config_path}")
            
        except Exception as e:
            print(f"❌ 配置文件加载失败: {e}")
            raise
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置值（支持点号分隔的路径）
        
        Args:
            key_path: 配置键路径，如 'email.recipients'
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_file_selection_config(self) -> Dict:
        """获取文件筛选配置"""
        return self.get('file_selection', {})
    
    def get_color_rules(self) -> Dict:
        """获取颜色规则配置"""
        return self.get('color_rules', {})
    
    def get_analysis_config(self) -> Dict:
        """获取数据分析配置"""
        return self.get('analysis', {})
    
    def get_image_config(self) -> Dict:
        """获取图片生成配置"""
        return self.get('image_generation', {})
    
    def get_email_config(self) -> Dict:
        """获取邮件发送配置"""
        return self.get('email', {})
    
    def get_output_config(self) -> Dict:
        """获取输出配置"""
        return self.get('output', {})
    
    def get_data_processing_config(self) -> Dict:
        """获取数据处理配置"""
        return self.get('data_processing', {})
    
    def is_email_enabled(self) -> bool:
        """判断是否启用邮件发送"""
        return self.get('email.enabled', False)
    
    def get_email_recipients(self) -> List[str]:
        """获取邮件收件人列表"""
        return self.get('email.recipients', [])
    
    def get_send_time_range(self) -> tuple:
        """
        获取邮件发送时间范围
        
        Returns:
            (start_time, end_time) 时间对象元组
        """
        start_str = self.get('email.send_times.start_time', '09:00')
        end_str = self.get('email.send_times.end_time', '18:00')
        
        # 解析时间字符串
        start_hour, start_min = map(int, start_str.split(':'))
        end_hour, end_min = map(int, end_str.split(':'))
        
        return time(start_hour, start_min), time(end_hour, end_min)
    
    def get_target_range(self) -> str:
        """获取目标处理区域"""
        return self.get('data_processing.target_range', 'A1:Z100')
    
    def get_screenshot_range(self) -> str:
        """获取截图区域"""
        return self.get('data_processing.screenshot_range', 'A1:M40')
    
    def get_analyzer_type(self) -> str:
        """获取分析器类型"""
        return self.get('analysis.analyzer_type', 'custom_analyzer')
    
    def get_file_pattern(self) -> str:
        """获取文件匹配模式"""
        return self.get('file_selection.pattern', '*')
    
    def get_time_limit_minutes(self) -> int:
        """获取时间限制（分钟）"""
        return self.get('file_selection.time_limit_minutes', 10)
    
    def get_search_paths(self) -> List[str]:
        """获取搜索路径列表"""
        return self.get('file_selection.search_paths', [])
    
    def get_column_width_config(self) -> Dict:
        """获取列宽配置"""
        return self.get('data_processing.column_width', {})
    
    def validate_config(self) -> bool:
        """
        验证配置文件的完整性
        
        Returns:
            配置是否有效
        """
        required_keys = [
            'name',
            'file_selection.pattern',
            'data_processing.target_range',
            'color_rules'
        ]
        
        for key in required_keys:
            if self.get(key) is None:
                print(f"❌ 配置验证失败：缺少必需项 '{key}'")
                return False
        
        print("✅ 配置验证通过")
        return True
    
    def print_config_summary(self) -> None:
        """打印配置摘要"""
        print(f"\n📋 === 配置摘要 ===")
        print(f"系统名称: {self.get('name', 'Unknown')}")
        print(f"版本: {self.get('version', 'Unknown')}")
        print(f"文件模式: {self.get_file_pattern()}")
        print(f"处理区域: {self.get_target_range()}")
        print(f"分析器: {self.get_analyzer_type()}")
        print(f"邮件发送: {'启用' if self.is_email_enabled() else '禁用'}")
        
        if self.is_email_enabled():
            start_time, end_time = self.get_send_time_range()
            print(f"发送时间: {start_time} - {end_time}")
            print(f"收件人数: {len(self.get_email_recipients())}")
        
        print("=" * 30)

if __name__ == "__main__":
    # 测试配置管理器
    config_file = "../configs/mt4_config.yaml"
    if os.path.exists(config_file):
        manager = ConfigManager(config_file)
        manager.print_config_summary()
    else:
        print(f"测试配置文件不存在: {config_file}")