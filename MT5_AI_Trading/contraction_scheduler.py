#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
收缩信号定时调度器
定时执行 contraction_alert_report.py 生成收缩报警报告
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
        logging.FileHandler('contraction_scheduler.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def run_contraction_report():
    """执行收缩报警报告脚本"""
    try:
        logger.info("开始执行 contraction_alert_report.py")
        
        # 获取MT5_AI_Trading目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(current_dir, 'contraction_alert_report.py')
        
        # 执行报告脚本
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            encoding='utf-8',
            cwd=current_dir
        )
        
        if result.returncode == 0:
            logger.info("contraction_alert_report.py 执行成功")
            # 输出报告内容到日志
            if result.stdout:
                logger.info(f"报告输出:\n{result.stdout}")
        else:
            logger.error("contraction_alert_report.py 执行失败")
            logger.error(f"错误: {result.stderr}")
            
    except Exception as e:
        logger.error(f"执行 contraction_alert_report.py 时发生异常: {str(e)}")


def run_full_analysis():
    """执行完整分析（交易机会 + 收缩报警）"""
    try:
        logger.info("开始执行完整分析")
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 1. 执行交易机会分析
        opp_script = os.path.join(current_dir, 'analyze_all_opportunities.py')
        result1 = subprocess.run(
            [sys.executable, opp_script],
            capture_output=True,
            text=True,
            encoding='utf-8',
            cwd=current_dir
        )
        
        if result1.returncode == 0:
            logger.info("analyze_all_opportunities.py 执行成功")
        else:
            logger.error(f"交易机会分析失败: {result1.stderr}")
        
        # 2. 执行收缩报警报告
        report_script = os.path.join(current_dir, 'contraction_alert_report.py')
        result2 = subprocess.run(
            [sys.executable, report_script],
            capture_output=True,
            text=True,
            encoding='utf-8',
            cwd=current_dir
        )
        
        if result2.returncode == 0:
            logger.info("contraction_alert_report.py 执行成功")
        else:
            logger.error(f"收缩报警报告失败: {result2.stderr}")
            
    except Exception as e:
        logger.error(f"执行完整分析时发生异常: {str(e)}")


def main(mode='report', immediate_run=False):
    """
    主函数
    
    Args:
        mode: 'report'仅收缩报告, 'full'完整分析, 'opportunities'仅交易机会
        immediate_run: 是否立即执行一次
    """
    logger.info("收缩信号定时调度器启动")
    logger.info(f"当前工作目录: {os.getcwd()}")
    logger.info(f"运行模式: {mode}")
    
    # 设置定时任务
    if mode == 'report':
        # 每4小时执行一次收缩报告
        schedule.every(4).hours.do(run_contraction_report)
        logger.info("定时任务: 每4小时执行收缩报警报告")
    elif mode == 'full':
        # 每4小时执行完整分析
        schedule.every(4).hours.do(run_full_analysis)
        logger.info("定时任务: 每4小时执行完整分析")
    elif mode == 'opportunities':
        # 仅交易机会分析
        opp_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                   'analyze_all_opportunities.py')
        schedule.every(4).hours.do(
            lambda: subprocess.run([sys.executable, opp_script], 
                                 capture_output=True, text=True, encoding='utf-8')
        )
        logger.info("定时任务: 每4小时执行交易机会分析")
    
    # 立即执行一次（用于测试）
    if immediate_run:
        logger.info("立即执行一次任务用于测试...")
        if mode == 'report':
            run_contraction_report()
        elif mode == 'full':
            run_full_analysis()
    else:
        logger.info("启动时不立即执行任务，等待定时执行...")
    
    logger.info("按Ctrl+C退出程序")
    
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
    parser = argparse.ArgumentParser(description='收缩信号定时调度器')
    parser.add_argument('--mode', choices=['report', 'full', 'opportunities'], 
                       default='report', help='运行模式')
    parser.add_argument('--immediate', action='store_true', 
                       help='是否立即执行一次任务')
    
    args = parser.parse_args()
    main(mode=args.mode, immediate_run=args.immediate)
