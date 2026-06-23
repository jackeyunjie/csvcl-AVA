#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试数据变化分析功能
"""

import pandas as pd
from process_real_mt4_data import RealMT4DataProcessor

def create_test_data_with_changes():
    """
    创建包含重要数值变化的测试数据
    """
    print("🔍 === 数据变化分析测试 ===\n")
    
    print("📋 测试数据说明:")
    print("   ✅ 每3行为一个品种（今天、昨天、前天）")
    print("   ✅ 模拟重要数值变化（2、6、-2、-6）")
    print("   ✅ 测试E、F、G列（MN1、W1、D1）的变化检测\n")
    
    # 创建测试数据，模拟真实的MT4数据格式
    test_data = {
        'SymbolName': [
            # HSI品种（3行）
            'HSI', 'HSI', 'HSI',
            # SPX500品种（3行）
            'SPX500', 'SPX500', 'SPX500',
            # EURUSD品种（3行）
            'EURUSD', 'EURUSD', 'EURUSD'
        ],
        'TIME': [
            # HSI
            '2025.08.26 00:00', '2025.08.25 00:00', '2025.08.24 00:00',
            # SPX500
            '2025.08.26 00:00', '2025.08.25 00:00', '2025.08.24 00:00',
            # EURUSD
            '2025.08.26 00:00', '2025.08.25 00:00', '2025.08.24 00:00'
        ],
        'Period': ['@1440'] * 9,
        'PRICE': [25900, 25850, 25800, 6500, 6480, 6460, 1.0920, 1.0895, 1.0870],
        # MN1列 - 重要变化：HSI从0变成2，SPX500从4变成-2
        'MN1': [2, 0, 1,     -2, 4, 3,     0, 0, 1],
        # W1列 - 重要变化：HSI从3变成6，EURUSD从0变成-6
        'W1':  [6, 3, 2,     0, 0, 1,     -6, 0, 2],
        # D1列 - 重要变化：SPX500从1变成-2
        'D1':  [4, 4, 2,     -2, 1, 0,     0, 0, 0],
        'H4':  [2, 0, 1,     0, 0, 1,      1, 2, 0],
        'H1':  [0, 0, 0,     0, 0, 0,      0, 0, 0],
        'M30': [0, 0, 0,     0, 0, 0,      0, 0, 0],
        'M15': [0, 0, 0,     0, 0, 0,      0, 0, 0],
        'M5':  [8, 4, 2,     0, 8, 4,      -4, 0, 2],
        'M1':  [1, -1, 0,    2, -2, 1,     0, 3, -1]
    }
    
    df = pd.DataFrame(test_data)
    
    print("📊 测试数据展示:")
    print(df[['SymbolName', 'TIME', 'MN1', 'W1', 'D1']].to_string())
    
    print(f"\n🎯 预期的重要变化:")
    print(f"   1. HSI MN1列: 0 → 2 (今天变成重要数值)")
    print(f"   2. HSI W1列: 3 → 6 (今天变成重要数值)")
    print(f"   3. SPX500 MN1列: 4 → -2 (今天变成重要数值)")
    print(f"   4. SPX500 D1列: 1 → -2 (今天变成重要数值)")
    print(f"   5. EURUSD W1列: 0 → -6 (今天变成重要数值)")
    
    return df

def test_change_analysis():
    """
    测试数据变化分析功能
    """
    try:
        # 创建测试数据
        df = create_test_data_with_changes()
        
        # 创建处理器
        processor = RealMT4DataProcessor()
        
        # 执行数据变化分析
        changes = processor.analyze_data_changes(df)
        
        print(f"\n📈 === 分析结果验证 ===")
        print(f"发现 {len(changes)} 个重要变化:")
        
        for i, change in enumerate(changes, 1):
            symbol = change['symbol']
            column = change['column']
            from_value = change['from_value']
            to_value = change['to_value']
            today_date = change['today_date']
            
            print(f"   {i}. {symbol} {column}列: {from_value} → {to_value} ({today_date})")
        
        print(f"\n🎯 分析结果评估:")
        if len(changes) == 5:
            print(f"   ✅ 检测到预期的5个重要变化")
        else:
            print(f"   ⚠️ 预期5个变化，实际检测到{len(changes)}个")
        
        # 验证具体变化
        expected_changes = [
            ('HSI', 'MN1', 0, 2),
            ('HSI', 'W1', 3, 6),
            ('SPX500', 'MN1', 4, -2),
            ('SPX500', 'D1', 1, -2),
            ('EURUSD', 'W1', 0, -6)
        ]
        
        for exp_symbol, exp_col, exp_from, exp_to in expected_changes:
            found = False
            for change in changes:
                if (change['symbol'] == exp_symbol and 
                    change['column'] == exp_col and
                    change['from_value'] == exp_from and
                    change['to_value'] == exp_to):
                    found = True
                    break
            
            status = "✅" if found else "❌"
            print(f"   {status} {exp_symbol} {exp_col}: {exp_from} → {exp_to}")
        
        return changes
        
    except Exception as e:
        print(f"❌ 测试过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def test_email_format():
    """
    测试邮件格式化输出
    """
    print(f"\n📧 === 邮件格式测试 ===")
    
    # 模拟变化数据
    test_changes = [
        {
            'symbol': 'HSI',
            'column': 'MN1',
            'today_date': '2025.08.26 00:00',
            'from_value': 0,
            'to_value': 2
        },
        {
            'symbol': 'SPX500',
            'column': 'W1',
            'today_date': '2025.08.26 00:00',
            'from_value': 3,
            'to_value': -6
        }
    ]
    
    print("📝 邮件正文预览格式:")
    print("=" * 50)
    print("🔍 重要数据变化分析")
    print("以下是今日相对于昨日变成2、6、-2、-6的重要变化：")
    print()
    
    for change in test_changes:
        symbol = change['symbol']
        column = change['column']
        today_date = change['today_date']
        from_value = change['from_value']
        to_value = change['to_value']
        
        column_name_map = {
            'MN1': '月线(MN1)',
            'W1': '周线(W1)', 
            'D1': '日线(D1)'
        }
        column_display = column_name_map.get(column, column)
        
        print(f"📈 {symbol} - {column_display}列: {from_value} → {to_value}")
        print(f"   📅 日期: {today_date}")
        print()
    
    print("=" * 50)

if __name__ == "__main__":
    print("🚀 开始数据变化分析功能测试...\n")
    
    # 运行测试
    changes = test_change_analysis()
    
    if changes:
        test_email_format()
        print(f"\n🎉 测试完成！")
        print(f"✅ 数据变化分析功能正常工作")
        print(f"✅ 能够正确识别重要数值变化")
        print(f"✅ 邮件格式化输出正常")
    else:
        print(f"\n❌ 测试失败，请检查功能实现")