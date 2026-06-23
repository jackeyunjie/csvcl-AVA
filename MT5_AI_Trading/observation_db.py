"""
关键观察数据库 - 记录收缩突破特征，支持长期复现提醒

数据库: data/observation_db.duckdb

核心表:
- observation_sessions: 观察会话（每次3天观察）
- daily_contraction_profiles: 每日收缩特征快照
- symbol_signatures: 品种收缩签名（用于复现匹配）
- reification_alerts: 复现提醒记录
"""

import os
import duckdb
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# 使用绝对路径，避免运行时目录分叉
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_SCRIPT_DIR, "data", "observation_db.duckdb")


def init_db():
    """初始化数据库"""
    db_dir = os.path.dirname(DB_PATH)
    os.makedirs(db_dir, exist_ok=True)
    
    conn = duckdb.connect(DB_PATH)
    
    # 观察会话表
    conn.execute("""
        CREATE SEQUENCE IF NOT EXISTS seq_session_id START 1;
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS observation_sessions (
            session_id INTEGER PRIMARY KEY DEFAULT nextval('seq_session_id'),
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            context TEXT,  -- 观察背景（如：非农前3天）
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 每日收缩特征快照
    conn.execute("""
        CREATE SEQUENCE IF NOT EXISTS seq_profile_id START 1;
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_contraction_profiles (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_profile_id'),
            session_id INTEGER,
            symbol VARCHAR(20) NOT NULL,
            date DATE NOT NULL,
            timeframe VARCHAR(10) NOT NULL,  -- H1, M15, etc.
            total_bars INTEGER,
            contraction_bars INTEGER,
            contraction_pct DOUBLE,
            transitions INTEGER,
            avg_contraction_duration DOUBLE,
            max_contraction_duration INTEGER,
            avg_breakout_move DOUBLE,
            up_breakout_pct DOUBLE,
            max_contraction_streak INTEGER,
            avg_contraction_streak DOUBLE,
            -- 价格信息
            open_price DOUBLE,
            high_price DOUBLE,
            low_price DOUBLE,
            close_price DOUBLE,
            daily_return_pct DOUBLE,
            -- 元数据
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES observation_sessions(session_id)
        )
    """)
    
    # 品种收缩签名（用于复现匹配）
    conn.execute("""
        CREATE SEQUENCE IF NOT EXISTS seq_signature_id START 1;
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS symbol_signatures (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_signature_id'),
            session_id INTEGER,
            symbol VARCHAR(20) NOT NULL,
            timeframe VARCHAR(10) NOT NULL,
            -- 3天综合签名
            total_bars INTEGER,
            total_contraction_bars INTEGER,
            overall_contraction_pct DOUBLE,
            total_transitions INTEGER,
            -- 收缩分布特征（JSON）
            daily_contraction_pattern VARCHAR(50),  -- 如: "0,4,0" 表示3天收缩分布
            -- 关键指标
            max_daily_contraction_pct DOUBLE,
            min_daily_contraction_pct DOUBLE,
            std_daily_contraction_pct DOUBLE,
            -- 签名哈希（用于快速匹配）
            signature_hash VARCHAR(64),
            -- 复现阈值配置
            reification_threshold DOUBLE DEFAULT 70.0,  -- 默认70%匹配度触发提醒
            -- 元数据
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES observation_sessions(session_id)
        )
    """)
    
    # 复现提醒记录
    conn.execute("""
        CREATE SEQUENCE IF NOT EXISTS seq_alert_id START 1;
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reification_alerts (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_alert_id'),
            reference_session_id INTEGER,  -- 参考的原始观察会话
            reference_symbol VARCHAR(20),
            alert_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            match_score DOUBLE,  -- 匹配度 0-100
            current_contraction_pct DOUBLE,
            reference_contraction_pct DOUBLE,
            similarity_details TEXT,  -- JSON格式详细对比
            alerted BOOLEAN DEFAULT FALSE,  -- 是否已提醒
            dismissed BOOLEAN DEFAULT FALSE,  -- 是否已忽略
            notes TEXT,
            FOREIGN KEY (reference_session_id) REFERENCES observation_sessions(session_id)
        )
    """)
    
    # 关键观察事件表（记录特殊市场状态）
    conn.execute("""
        CREATE SEQUENCE IF NOT EXISTS seq_obs_id START 1;
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS key_observations (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_obs_id'),
            session_id INTEGER,
            observation_date DATE,
            symbol VARCHAR(20),
            timeframe VARCHAR(10),
            observation_type VARCHAR(50),  -- contraction_cluster, breakout, range_bound, etc.
            description TEXT,
            severity INTEGER DEFAULT 1,  -- 1=普通, 2=重要, 3=关键
            tags TEXT,  -- JSON数组
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES observation_sessions(session_id)
        )
    """)
    
    conn.commit()
    conn.close()
    print(f"数据库初始化完成: {DB_PATH}")


def save_observation_session(start_date: str, end_date: str, context: str = "") -> int:
    """保存观察会话，返回session_id。如果同周期同context已存在则复用。"""
    conn = duckdb.connect(DB_PATH)
    
    # 幂等检查：同周期同context视为同一观察
    existing = conn.execute("""
        SELECT session_id FROM observation_sessions
        WHERE start_date = ? AND end_date = ? AND context = ?
    """, [start_date, end_date, context]).fetchone()
    
    if existing:
        session_id = existing[0]
        conn.close()
        return session_id
    
    result = conn.execute("""
        INSERT INTO observation_sessions (start_date, end_date, context)
        VALUES (?, ?, ?)
        RETURNING session_id
    """, [start_date, end_date, context]).fetchone()
    
    session_id = result[0]
    conn.commit()
    conn.close()
    return session_id


def save_daily_profiles(session_id: int, profiles: List[Dict]):
    """保存每日收缩特征（幂等：同session同symbol同date同tf不重复插入）"""
    conn = duckdb.connect(DB_PATH)
    
    for profile in profiles:
        # 幂等检查
        existing = conn.execute("""
            SELECT id FROM daily_contraction_profiles
            WHERE session_id = ? AND symbol = ? AND date = ? AND timeframe = ?
        """, [session_id, profile['symbol'], profile['date'], profile['timeframe']]).fetchone()
        
        if existing:
            continue  # 已存在，跳过
        
        conn.execute("""
            INSERT INTO daily_contraction_profiles (
                session_id, symbol, date, timeframe,
                total_bars, contraction_bars, contraction_pct,
                transitions, avg_contraction_duration, max_contraction_duration,
                avg_breakout_move, up_breakout_pct,
                max_contraction_streak, avg_contraction_streak,
                open_price, high_price, low_price, close_price, daily_return_pct
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            session_id, profile['symbol'], profile['date'], profile['timeframe'],
            profile.get('total_bars'), profile.get('contraction_bars'), profile.get('contraction_pct'),
            profile.get('transitions'), profile.get('avg_contraction_duration'), profile.get('max_contraction_duration'),
            profile.get('avg_breakout_move'), profile.get('up_breakout_pct'),
            profile.get('max_contraction_streak'), profile.get('avg_contraction_streak'),
            profile.get('open_price'), profile.get('high_price'), profile.get('low_price'), 
            profile.get('close_price'), profile.get('daily_return_pct')
        ])
    
    conn.commit()
    conn.close()


def save_symbol_signature(session_id: int, symbol: str, timeframe: str, 
                          signature: Dict, threshold: float = 70.0):
    """保存品种收缩签名（幂等：同session同symbol同tf不重复插入）"""
    conn = duckdb.connect(DB_PATH)
    
    # 幂等检查
    existing = conn.execute("""
        SELECT id FROM symbol_signatures
        WHERE session_id = ? AND symbol = ? AND timeframe = ?
    """, [session_id, symbol, timeframe]).fetchone()
    
    if existing:
        conn.close()
        return  # 已存在，跳过
    
    # 生成签名哈希
    pattern = signature.get('daily_pattern', '')
    hash_input = f"{symbol}_{timeframe}_{pattern}_{signature.get('overall_contraction_pct', 0):.1f}"
    import hashlib
    signature_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    conn.execute("""
        INSERT INTO symbol_signatures (
            session_id, symbol, timeframe,
            total_bars, total_contraction_bars, overall_contraction_pct,
            total_transitions, daily_contraction_pattern,
            max_daily_contraction_pct, min_daily_contraction_pct, std_daily_contraction_pct,
            signature_hash, reification_threshold
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        session_id, symbol, timeframe,
        signature.get('total_bars'), signature.get('total_contraction_bars'),
        signature.get('overall_contraction_pct'), signature.get('total_transitions'),
        pattern, signature.get('max_daily_pct'), signature.get('min_daily_pct'),
        signature.get('std_daily_pct'), signature_hash, threshold
    ])
    
    conn.commit()
    conn.close()


def save_key_observation(session_id: int, date: str, symbol: str, timeframe: str,
                        obs_type: str, description: str, severity: int = 1, tags: List[str] = None):
    """保存关键观察事件（幂等：同session同symbol同date同type不重复插入）"""
    conn = duckdb.connect(DB_PATH)
    
    # 幂等检查
    existing = conn.execute("""
        SELECT id FROM key_observations
        WHERE session_id = ? AND observation_date = ? AND symbol = ? 
          AND timeframe = ? AND observation_type = ?
    """, [session_id, date, symbol, timeframe, obs_type]).fetchone()
    
    if existing:
        conn.close()
        return  # 已存在，跳过
    
    tags_json = str(tags) if tags else "[]"
    
    conn.execute("""
        INSERT INTO key_observations (session_id, observation_date, symbol, timeframe,
                                     observation_type, description, severity, tags)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, [session_id, date, symbol, timeframe, obs_type, description, severity, tags_json])
    
    conn.commit()
    conn.close()


def _calculate_match_score(current_profile: Dict, reference_row) -> Tuple[float, Dict]:
    """
    四维加权匹配算法
    
    维度权重:
    1. 整体收缩占比相似度: 35%
    2. 单日最大收缩占比相似度: 25%
    3. 收缩分布标准差相似度: 20%
    4. 品种一致性: 20%
    """
    score = 0.0
    details = {}
    
    # 1. 整体收缩占比 (35%)
    current_pct = current_profile.get('contraction_pct', 0)
    ref_pct = reference_row['overall_contraction_pct']
    if ref_pct > 0:
        pct_sim = max(0, 100 - abs(current_pct - ref_pct) / ref_pct * 100)
    else:
        pct_sim = 100 if current_pct == 0 else 0
    score += pct_sim * 0.35
    details['contraction_pct'] = round(pct_sim, 1)
    
    # 2. 单日最大收缩 (25%) - 检测极端收缩日
    curr_max = current_profile.get(
        'max_daily_pct',
        current_profile.get('max_contraction_streak', 0),
    )
    ref_max = reference_row['max_daily_contraction_pct']
    if ref_max > 0:
        max_sim = max(0, 100 - abs(curr_max - ref_max) / ref_max * 100)
    else:
        max_sim = 100 if curr_max == 0 else 0
    score += max_sim * 0.25
    details['max_daily'] = round(max_sim, 1)
    
    # 3. 分布标准差 (20%) - 检测收缩集中度
    curr_std = current_profile.get(
        'std_daily_pct',
        current_profile.get('contraction_pct', 0) * 0.5,
    )
    ref_std = reference_row['std_daily_contraction_pct']
    if ref_std > 0:
        std_sim = max(0, 100 - abs(curr_std - ref_std) / ref_std * 100)
    else:
        std_sim = 100 if curr_std == 0 else 0
    score += std_sim * 0.20
    details['std'] = round(std_sim, 1)
    
    # 4. 品种一致性 (20%)
    score += 20.0
    details['symbol'] = 100.0
    
    final_score = min(100.0, score)
    return round(final_score, 1), details


def check_reification(symbol: str, timeframe: str, current_profile: Dict, 
                     threshold: float = None) -> List[Dict]:
    """
    检查当前品种是否复现了历史观察特征
    
    优先使用签名自己配置的阈值(reification_threshold)，
    仅在未配置时使用传入的threshold参数（默认70.0）
    """
    conn = duckdb.connect(DB_PATH)
    
    # 获取历史签名
    historical = conn.execute("""
        SELECT s.*, sess.start_date, sess.end_date, sess.context
        FROM symbol_signatures s
        JOIN observation_sessions sess ON s.session_id = sess.session_id
        WHERE s.symbol = ? AND s.timeframe = ?
        ORDER BY sess.start_date DESC
    """, [symbol, timeframe]).fetchdf()
    
    if historical.empty:
        conn.close()
        return []
    
    alerts = []
    
    for _, row in historical.iterrows():
        # 使用签名自己的阈值，未配置则使用默认值70.0
        sig_threshold = row['reification_threshold']
        if pd.isna(sig_threshold) or sig_threshold is None:
            sig_threshold = threshold if threshold is not None else 70.0
        
        # 使用统一的四维加权算法计算匹配度
        final_score, details = _calculate_match_score(current_profile, row)
        
        if final_score >= sig_threshold:
            alerts.append({
                'reference_session_id': row['session_id'],
                'reference_symbol': symbol,
                'match_score': final_score,
                'current_contraction_pct': current_profile.get('contraction_pct', 0),
                'reference_contraction_pct': row['overall_contraction_pct'],
                'reference_period': f"{row['start_date']} to {row['end_date']}",
                'reference_context': row['context'],
                'similarity_details': str(details),
                'threshold_used': sig_threshold
            })
    
    conn.close()
    return alerts


def save_reification_alert(alert: Dict):
    """保存复现提醒"""
    conn = duckdb.connect(DB_PATH)
    
    conn.execute("""
        INSERT INTO reification_alerts (
            reference_session_id, reference_symbol, match_score,
            current_contraction_pct, reference_contraction_pct, similarity_details
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, [
        alert['reference_session_id'], alert['reference_symbol'], alert['match_score'],
        alert['current_contraction_pct'], alert['reference_contraction_pct'], 
        alert['similarity_details']
    ])
    
    conn.commit()
    conn.close()


def get_pending_alerts() -> pd.DataFrame:
    """获取待处理的复现提醒"""
    conn = duckdb.connect(DB_PATH)
    
    df = conn.execute("""
        SELECT a.*, s.start_date, s.end_date, s.context
        FROM reification_alerts a
        JOIN observation_sessions s ON a.reference_session_id = s.session_id
        WHERE a.alerted = FALSE AND a.dismissed = FALSE
        ORDER BY a.match_score DESC
    """).fetchdf()
    
    conn.close()
    return df


def get_session_summary(session_id: int) -> Dict:
    """获取观察会话摘要"""
    conn = duckdb.connect(DB_PATH)
    
    session = conn.execute("""
        SELECT * FROM observation_sessions WHERE session_id = ?
    """, [session_id]).fetchone()
    
    profiles = conn.execute("""
        SELECT symbol, timeframe, 
               AVG(contraction_pct) as avg_contraction_pct,
               SUM(transitions) as total_transitions,
               COUNT(DISTINCT date) as days_observed
        FROM daily_contraction_profiles
        WHERE session_id = ?
        GROUP BY symbol, timeframe
    """, [session_id]).fetchdf()
    
    conn.close()
    
    return {
        'session_id': session_id,
        'period': f"{session[1]} to {session[2]}" if session else "",
        'context': session[3] if session else "",
        'profiles': profiles.to_dict('records') if not profiles.empty else []
    }


def export_session_to_md(session_id: int, output_path: str = None):
    """导出观察会话为Markdown报告"""
    conn = duckdb.connect(DB_PATH)
    
    session = conn.execute("""
        SELECT * FROM observation_sessions WHERE session_id = ?
    """, [session_id]).fetchone()
    
    if not session:
        conn.close()
        return
    
    profiles = conn.execute("""
        SELECT * FROM daily_contraction_profiles
        WHERE session_id = ?
        ORDER BY symbol, timeframe, date
    """, [session_id]).fetchdf()
    
    observations = conn.execute("""
        SELECT * FROM key_observations
        WHERE session_id = ?
        ORDER BY severity DESC, observation_date
    """, [session_id]).fetchdf()
    
    conn.close()
    
    lines = []
    lines.append(f"# 观察会话报告 #{session_id}")
    lines.append(f"\n> 观察周期: {session[1]} 至 {session[2]}")
    lines.append(f"> 背景: {session[3]}")
    lines.append(f"> 记录时间: {session[4]}")
    
    if not profiles.empty:
        lines.append("\n## 每日收缩特征")
        lines.append("\n| 品种 | 周期 | 日期 | 总Bar | 收缩Bar | 收缩% | 突破次数 |")
        lines.append("|------|------|------|-------|---------|-------|----------|")
        for _, row in profiles.iterrows():
            lines.append(f"| {row['symbol']} | {row['timeframe']} | {row['date']} | "
                        f"{row['total_bars']} | {row['contraction_bars']} | "
                        f"{row['contraction_pct']:.1f}% | {row['transitions']} |")
    
    if not observations.empty:
        lines.append("\n## 关键观察事件")
        for _, row in observations.iterrows():
            severity_label = "🔴" if row['severity'] == 3 else "🟡" if row['severity'] == 2 else "⚪"
            lines.append(f"\n### {severity_label} {row['observation_type']} ({row['observation_date']})")
            lines.append(f"- 品种: {row['symbol']} ({row['timeframe']})")
            lines.append(f"- 描述: {row['description']}")
            if row['tags']:
                lines.append(f"- 标签: {row['tags']}")
    
    lines.append("\n---")
    lines.append("> 本报告由观察数据库自动生成")
    
    if output_path is None:
        output_path = f"reports/squeeze/observation_session_{session_id}.md"
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    return output_path


# ========================================================================
# 便捷函数：保存本次观察
# ========================================================================

def save_current_observation(observation_data: Dict):
    """
    保存本次观察数据到数据库
    
    observation_data格式:
    {
        'start_date': '2026-06-03',
        'end_date': '2026-06-05',
        'context': '非农前3天观察',
        'profiles': [...],  # 每日特征列表
        'signatures': [...],  # 品种签名列表
        'key_observations': [...]  # 关键观察事件
    }
    """
    # 初始化数据库
    init_db()
    
    # 保存会话
    session_id = save_observation_session(
        observation_data['start_date'],
        observation_data['end_date'],
        observation_data.get('context', '')
    )
    
    # 保存每日特征
    if 'profiles' in observation_data:
        for profile in observation_data['profiles']:
            profile['session_id'] = session_id
        save_daily_profiles(session_id, observation_data['profiles'])
    
    # 保存签名
    if 'signatures' in observation_data:
        for sig in observation_data['signatures']:
            save_symbol_signature(
                session_id, sig['symbol'], sig['timeframe'],
                sig, sig.get('threshold', 70.0)
            )
    
    # 保存关键观察
    if 'key_observations' in observation_data:
        for obs in observation_data['key_observations']:
            save_key_observation(
                session_id, obs['date'], obs['symbol'], obs['timeframe'],
                obs['type'], obs['description'], obs.get('severity', 1), obs.get('tags')
            )
    
    print(f"\n观察数据已保存到数据库，会话ID: {session_id}")
    return session_id


if __name__ == "__main__":
    # 测试数据库初始化
    init_db()
    print("数据库初始化完成，可以开始记录观察数据")
