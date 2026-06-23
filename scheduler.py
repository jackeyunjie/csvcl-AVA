#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时调度器
用于定时执行auto_email_config.py脚本
每天7:03运行，不使用Windows任务计划程序
"""

import schedule
import time
import subprocess
import sys
import os
from datetime import datetime
import logging
import argparse

# 设置编码以避免Windows乱码问题
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def run_auto_email():
    """执行auto_email_config.py脚本"""
    try:
        logger.info("开始执行auto_email_config.py")
        
        # 获取当前脚本所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(current_dir, 'auto_email_config.py')
        
        # 执行auto_email_config.py脚本
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            encoding='utf-8',
            cwd=current_dir
        )
        
        if result.returncode == 0:
            logger.info("auto_email_config.py执行成功")
            logger.info(f"输出: {result.stdout}")
        else:
            logger.error("auto_email_config.py执行失败")
            logger.error(f"错误: {result.stderr}")
            
    except Exception as e:
        logger.error(f"执行auto_email_config.py时发生异常: {str(e)}")

def main(immediate_run=False):
    """主函数"""
    logger.info("定时调度器启动")
    logger.info(f"当前工作目录: {os.getcwd()}")
    
    # 设置每天早上7:03执行（根据用户需求修改时间）
    schedule.every().day.at("07:03").do(run_auto_email)
    
    logger.info("定时任务已设置: 每天早上7:03执行auto_email_config.py")
    logger.info("按Ctrl+C退出程序")
    
    # 根据参数决定是否立即执行一次（用于测试）
    if immediate_run:
        logger.info("立即执行一次任务用于测试...")
        run_auto_email()
    else:
        logger.info("启动时不立即执行任务，等待定时执行...")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
            
            # 显示下一次执行时间
            next_run = schedule.next_run()
            if next_run:
                logger.info(f"下次执行时间: {next_run.strftime('%Y-%m-%d %H:%M')}")
    except KeyboardInterrupt:
        logger.info("定时调度器已停止")
        sys.exit(0)
    except Exception as e:
        logger.error(f"定时调度器发生异常: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='定时调度器')
    parser.add_argument('--immediate', action='store_true', help='是否立即执行一次任务')
    
    args = parser.parse_args()
    main(immediate_run=args.immediate)