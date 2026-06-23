"""
P107 / P106 合规验证脚本

验证内容:
1. State Hex 编码合规（P107）
   - 最小分析单元是三元组(MN1, W1, D1)
   - 禁止单独分析日线D1
   - 禁止忽略MN1和W1只看D1
   - state_hex是体检码，不是线性分数，不是买卖许可
   - D1/H1/M15是独立原生系统

2. 资金流定位合规（P106）
   - 资金流不替代价格状态主裁决
   - 资金流不替代P17状态组合窗口验证
   - 主线顺序：状态对齐 → 策略条件 → 成交活跃 → 资金流 → 筹码峰

3. 语义边界合规
   - 不出现动作语义（"买入""跟进""必涨""必守"）
   - reasoning保持解释性语义
   - 只输出研究标签，不输出动作建议

4. 代码结构合规
   - State Hex引擎存在且可导入
   - MoneyflowEnergyLayer存在且可导入
   - TradingStrategy使用State Hex而非旧技术指标

用法:
    python scripts/verify_p107_p106.py [--codebase-dir DIR] [--verbose]
"""

import os
import sys
import re
import ast
import argparse
import importlib.util
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum


class CheckLevel(Enum):
    CRITICAL = "CRITICAL"    # 违反核心第一性原理
    ERROR = "ERROR"          # 违反规范
    WARNING = "WARNING"      # 潜在风险
    INFO = "INFO"            # 信息提示


@dataclass
class Violation:
    level: CheckLevel
    rule: str
    file: str
    line: int
    message: str
    suggestion: str = ""


class P107P106Verifier:
    """
    P107/P106 合规验证器

    对代码库进行静态分析，检查是否违反P107 State Hex规范和P106资金流规范。
    """

    # P107 核心第一性原理 —— 不可违背
    CRITICAL_RULES = {
        "P107-TRIPLET": "最小分析单元必须是三元组(MN1, W1, D1)",
        "P107-NO-D1-ALONE": "禁止单独分析日线D1",
        "P107-NO-IGNORE-HIGH": "禁止忽略MN1和W1只看D1",
        "P107-HEX-NOT-SCORE": "state_hex是体检码，不是线性分数",
        "P107-HEX-NOT-ACTION": "state_hex不是买卖许可",
        "P106-MF-NOT-STATE": "资金流不替代价格状态",
        "P106-MF-NOT-BYPASS": "资金流不替代P17状态组合窗口验证",
        "P106-NO-ACTION-SEM": "不出现动作语义",
    }

    # 动作语义关键词（禁止出现）
    ACTION_KEYWORDS = [
        r"应该跟进", r"应该买入", r"应该卖出", r"立即买入", r"立即卖出",
        r"主力买入.*跟进", r"跟进买入", r"跟进卖出",
        r"必涨", r"必跌", r"必守", r"必破",
        r"一定上涨", r"一定下跌", r"一定好",
        r"可以直接买", r"可以直接卖",
        r"最强.*买", r"最强.*卖",
        r"买入信号", r"卖出信号",
        r"做多", r"做空", r"开仓", r"平仓.*建议",
    ]

    # 单周期分析关键词（警告）
    SINGLE_TF_KEYWORDS = [
        r"只看D1", r"只看日线", r"单独看D1", r"单独分析D1",
        r"忽略MN1", r"忽略月线", r"忽略W1", r"忽略周线",
        r"D1单独", r"日线单独",
    ]

    def __init__(self, codebase_dir: str, verbose: bool = False):
        self.codebase_dir = Path(codebase_dir)
        self.verbose = verbose
        self.violations: List[Violation] = []
        self.python_files: List[Path] = []
        self._scan_files()

    def _scan_files(self):
        """扫描Python文件"""
        for pyfile in self.codebase_dir.rglob("*.py"):
            # 排除__pycache__和第三方库
            if "__pycache__" in str(pyfile) or "site-packages" in str(pyfile):
                continue
            self.python_files.append(pyfile)

        if self.verbose:
            print(f"扫描文件数: {len(self.python_files)}")

    # ========================================================================
    # 检查1: State Hex 编码合规
    # ========================================================================

    def check_state_hex_compliance(self):
        """检查State Hex编码合规"""
        print("\n[检查1] State Hex 编码合规...")

        # 1.1 检查state_hex_encoding.py是否存在
        state_hex_file = self._find_file("state_hex_encoding.py")
        if state_hex_file:
            self._check_state_hex_encoder(state_hex_file)
        else:
            self._add_violation(
                CheckLevel.CRITICAL, "P107-HEX-NOT-SCORE",
                "", 0,
                "未找到state_hex_encoding.py",
                "确保State Hex编码模块存在"
            )

        # 1.2 检查StateHexEngine是否存在
        engine_file = self._find_file("state_hex_engine.py")
        if engine_file:
            self._check_state_engine(engine_file)
        else:
            self._add_violation(
                CheckLevel.CRITICAL, "P107-TRIPLET",
                "", 0,
                "未找到state_hex_engine.py",
                "确保State Hex引擎存在"
            )

        # 1.3 检查trading_strategy.py是否使用State Hex
        strategy_file = self._find_file("trading_strategy.py")
        if strategy_file:
            self._check_strategy_uses_state_hex(strategy_file)

    def _check_state_hex_encoder(self, filepath: Path):
        """检查StateHexEncoder实现"""
        content = filepath.read_text(encoding='utf-8')

        # 检查是否有encode/decode方法
        if 'def encode' not in content:
            self._add_violation(
                CheckLevel.ERROR, "P107-HEX-NOT-SCORE",
                str(filepath), 0,
                "StateHexEncoder缺少encode方法",
                "实现encode方法将组件编码为state_hex"
            )

        if 'def decode' not in content:
            self._add_violation(
                CheckLevel.ERROR, "P107-HEX-NOT-SCORE",
                str(filepath), 0,
                "StateHexEncoder缺少decode方法",
                "实现decode方法解析state_hex为组件"
            )

        # 检查是否将state_hex当分数使用（危险信号）
        dangerous_patterns = [
            (r'state_hex.*[<>]=?\s*\d', "将state_hex与数字比较大小"),
            (r'state_hex.*排序', "对state_hex排序"),
            (r'state_hex.*排名', "对state_hex排名"),
            (r'state_hex.*最强', "将state_hex描述为最强"),
        ]

        for pattern, desc in dangerous_patterns:
            if re.search(pattern, content):
                self._add_violation(
                    CheckLevel.CRITICAL, "P107-HEX-NOT-SCORE",
                    str(filepath), 0,
                    f"可能将state_hex当线性分数使用: {desc}",
                    "state_hex是体检码，不是分数，禁止排序/比较大小"
                )

        # 检查正负号处理
        if 'signed' not in content and '正负' not in content:
            self._add_violation(
                CheckLevel.WARNING, "P107-HEX-NOT-SCORE",
                str(filepath), 0,
                "StateHexEncoder可能未正确处理方向（正负号）",
                "确保正负号表示多向/空向语境"
            )

    def _check_state_engine(self, filepath: Path):
        """检查StateHexEngine实现"""
        content = filepath.read_text(encoding='utf-8')

        # 检查是否输出三元组
        if 'triplet' not in content.lower() and '三元组' not in content:
            self._add_violation(
                CheckLevel.CRITICAL, "P107-TRIPLET",
                str(filepath), 0,
                "StateHexEngine未输出三元组",
                "必须输出(MN1, W1, D1)三元组作为最小分析单元"
            )

        # 检查是否聚合W1/MN1
        if 'w1' not in content.lower() and 'W1' not in content:
            self._add_violation(
                CheckLevel.CRITICAL, "P107-TRIPLET",
                str(filepath), 0,
                "KVBStateHexEngine未处理W1周期",
                "必须从D1聚合计算W1 state_hex"
            )

        if 'mn1' not in content.lower() and 'MN1' not in content:
            self._add_violation(
                CheckLevel.CRITICAL, "P107-TRIPLET",
                str(filepath), 0,
                "KVBStateHexEngine未处理MN1周期",
                "必须从D1聚合计算MN1 state_hex"
            )

        # 检查是否有独立原生系统声明
        if 'native' not in content.lower() and '原生' not in content:
            self._add_violation(
                CheckLevel.WARNING, "P107-NO-D1-ALONE",
                str(filepath), 0,
                "未声明base-timeframe native系统原则",
                "在文档或注释中声明D1/H1/M15是独立原生系统"
            )

    def _check_strategy_uses_state_hex(self, filepath: Path):
        """检查策略是否使用State Hex而非旧技术指标"""
        content = filepath.read_text(encoding='utf-8')

        # 检查是否导入State Hex相关模块
        has_state_hex_import = (
            'state_hex' in content.lower() or
            'kvb_state' in content.lower()
        )

        if not has_state_hex_import:
            self._add_violation(
                CheckLevel.CRITICAL, "P107-TRIPLET",
                str(filepath), 0,
                "TradingStrategy未导入State Hex模块",
                "策略必须基于State Hex三元组进行状态判断"
            )

        # 检查是否仍依赖旧技术指标生成信号
        old_indicators = ['EMA', 'MACD', 'RSI', 'Stochastic']
        for ind in old_indicators:
            if ind in content:
                # 如果只是保留兼容层，不算违规
                if 'def calculate_indicators' in content or 'TechnicalIndicators' in content:
                    self._add_violation(
                        CheckLevel.WARNING, "P107-TRIPLET",
                        str(filepath), 0,
                        f"TradingStrategy仍包含旧技术指标({ind})",
                        "确保旧指标仅用于价格行为验证，不作为信号主裁决"
                    )
                    break

        # 检查是否使用三元组做状态门
        if 'triplet' not in content.lower() and '三元组' not in content:
            self._add_violation(
                CheckLevel.CRITICAL, "P107-TRIPLET",
                str(filepath), 0,
                "TradingStrategy未使用三元组",
                "策略必须以(MN1, W1, D1)三元组为最小分析单元"
            )

    # ========================================================================
    # 检查2: 资金流定位合规
    # ========================================================================

    def check_moneyflow_compliance(self):
        """检查资金流定位合规"""
        print("\n[检查2] 资金流定位合规...")

        # 2.1 检查MoneyflowEnergyLayer是否存在
        mf_file = self._find_file("moneyflow_energy_layer.py")
        if mf_file:
            self._check_moneyflow_layer(mf_file)
        else:
            self._add_violation(
                CheckLevel.WARNING, "P106-MF-NOT-STATE",
                "", 0,
                "未找到moneyflow_energy_layer.py",
                "创建P106资金流能量增量层模块"
            )

        # 2.2 检查所有Python文件中的资金流使用
        self._check_moneyflow_usage_in_codebase()

    def _check_moneyflow_layer(self, filepath: Path):
        """检查MoneyflowEnergyLayer实现"""
        content = filepath.read_text(encoding='utf-8')

        # 检查是否拆成4个子维度
        required_dimensions = [
            'flow_direction_score',
            'flow_persistence_score',
            'flow_structure_score',
            'chip_structure_score',
        ]
        for dim in required_dimensions:
            if dim not in content:
                self._add_violation(
                    CheckLevel.ERROR, "P106-MF-NOT-STATE",
                    str(filepath), 0,
                    f"MoneyflowEnergyLayer缺少子维度: {dim}",
                    "P106要求拆成4个子维度评分，不合成单一买入分"
                )

        # 检查是否输出研究标签而非动作建议
        if 'research_tags' not in content and '研究标签' not in content:
            self._add_violation(
                CheckLevel.ERROR, "P106-NO-ACTION-SEM",
                str(filepath), 0,
                "MoneyflowEnergyLayer未输出研究标签",
                "只输出研究标签（energy_supportive等），不输出动作建议"
            )

        # 检查是否有正确的定位声明
        if '不替代' not in content and 'secondary' not in content.lower():
            self._add_violation(
                CheckLevel.WARNING, "P106-MF-NOT-STATE",
                str(filepath), 0,
                "未声明资金流是二级确认",
                "在模块文档中声明资金流只做二级确认和解释增强"
            )

    def _check_moneyflow_usage_in_codebase(self):
        """检查代码库中资金流的使用方式"""
        for pyfile in self.python_files:
            content = pyfile.read_text(encoding='utf-8')

            # 检查是否将资金流作为主裁决
            dangerous_patterns = [
                (r'主力.*买入.*信号', "主力买入生成信号"),
                (r'净流入.*大于.*买入', "净流入直接触发买入"),
                (r'moneyflow.*signal', "moneyflow直接生成signal"),
                (r'资金.*决定.*交易', "资金流决定交易"),
            ]

            for pattern, desc in dangerous_patterns:
                matches = list(re.finditer(pattern, content))
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    self._add_violation(
                        CheckLevel.CRITICAL, "P106-MF-NOT-STATE",
                        str(pyfile), line_num,
                        f"资金流可能被用作主裁决: {desc}",
                        "资金流只能做二级确认，不能替代价格状态主裁决"
                    )

    # ========================================================================
    # 检查3: 语义边界合规
    # ========================================================================

    def _is_line_exempt(self, content: str, match_start: int) -> bool:
        """检查匹配行是否有豁免标记"""
        line_start = content.rfind('\n', 0, match_start) + 1
        line_end = content.find('\n', match_start)
        if line_end == -1:
            line_end = len(content)
        line = content[line_start:line_end]
        return '# verify-exempt' in line

    def check_semantic_compliance(self):
        """检查语义边界合规"""
        print("\n[检查3] 语义边界合规...")

        for pyfile in self.python_files:
            content = pyfile.read_text(encoding='utf-8')

            # 检查动作语义
            for pattern in self.ACTION_KEYWORDS:
                matches = list(re.finditer(pattern, content))
                for match in matches:
                    if self._is_line_exempt(content, match.start()):
                        continue
                    line_num = content[:match.start()].count('\n') + 1
                    self._add_violation(
                        CheckLevel.CRITICAL, "P106-NO-ACTION-SEM",
                        str(pyfile), line_num,
                        f"发现动作语义: {match.group()}",
                        "替换为解释性语义，如'资金关注增强'而非'主力买入，应该跟进'"
                    )

            # 检查单周期分析语义（排除有豁免标记的行）
            for pattern in self.SINGLE_TF_KEYWORDS:
                matches = list(re.finditer(pattern, content))
                for match in matches:
                    if self._is_line_exempt(content, match.start()):
                        continue
                    line_num = content[:match.start()].count('\n') + 1
                    self._add_violation(
                        CheckLevel.ERROR, "P107-NO-D1-ALONE",
                        str(pyfile), line_num,
                        f"发现单周期分析语义: {match.group()}",
                        "必须将(MN1, W1, D1)作为最小分析单元，禁止单独看D1"
                    )

    # ========================================================================
    # 检查4: 主线顺序合规
    # ========================================================================

    def check_pipeline_order(self):
        """检查主线顺序合规"""
        print("\n[检查4] 主线顺序合规...")

        strategy_file = self._find_file("trading_strategy.py")
        if not strategy_file:
            return

        content = strategy_file.read_text(encoding='utf-8')

        # 检查主线顺序：状态对齐 → 策略条件 → 成交活跃 → 资金流 → 筹码峰
        # 简化检查：确保资金流检查在状态检查之后

        # 查找关键函数的位置
        lines = content.split('\n')

        state_check_line = -1
        moneyflow_check_line = -1

        for i, line in enumerate(lines):
            if 'state_alignment' in line or 'state_hex' in line or 'triplet' in line:
                if state_check_line == -1:
                    state_check_line = i
            if 'moneyflow' in line.lower() or 'energy' in line.lower():
                if moneyflow_check_line == -1:
                    moneyflow_check_line = i

        if moneyflow_check_line != -1 and state_check_line != -1:
            if moneyflow_check_line < state_check_line:
                self._add_violation(
                    CheckLevel.CRITICAL, "P106-MF-NOT-BYPASS",
                    str(strategy_file), moneyflow_check_line + 1,
                    "资金流检查在状态检查之前",
                    "主线顺序必须是：状态对齐 → 策略条件 → 成交活跃 → 资金流 → 筹码峰"
                )

    # ========================================================================
    # 检查5: 模块可导入性
    # ========================================================================

    def check_importability(self):
        """检查关键模块是否可以导入"""
        print("\n[检查5] 模块可导入性...")

        modules_to_check = [
            ("ai_engine.state_hex_encoding", "StateHexEncoder"),
            ("ai_engine.kvb_state_hex_engine", "KVBStateHexEngine"),
            ("ai_engine.trading_strategy", "TradingStrategy"),
            ("ai_engine.moneyflow_energy_layer", "MoneyflowEnergyLayer"),
        ]

        for module_name, class_name in modules_to_check:
            found = self._check_module_importable(module_name, class_name)
            if not found:
                self._add_violation(
                    CheckLevel.ERROR, "P107-TRIPLET",
                    "", 0,
                    f"无法导入 {module_name}.{class_name}",
                    f"确保模块存在且类已定义"
                )

    def _check_module_importable(self, module_name: str, class_name: str) -> bool:
        """检查模块是否可导入"""
        # 将模块名转为文件路径
        parts = module_name.split('.')
        rel_path = os.path.join(*parts) + ".py"

        # 在代码库中查找
        for pyfile in self.python_files:
            if pyfile.name == parts[-1] + ".py":
                content = pyfile.read_text(encoding='utf-8')
                if f"class {class_name}" in content:
                    return True
        return False

    # ========================================================================
    # 辅助方法
    # ========================================================================

    def _find_file(self, filename: str) -> Optional[Path]:
        """查找文件"""
        for pyfile in self.python_files:
            if pyfile.name == filename:
                return pyfile
        return None

    def _add_violation(self, level: CheckLevel, rule: str, file: str, line: int,
                       message: str, suggestion: str = ""):
        """添加违规记录"""
        self.violations.append(Violation(
            level=level,
            rule=rule,
            file=file,
            line=line,
            message=message,
            suggestion=suggestion
        ))

    # ========================================================================
    # 报告生成
    # ========================================================================

    def run_all_checks(self):
        """运行所有检查"""
        print("=" * 70)
        print("P107 / P106 合规验证")
        print("=" * 70)
        print(f"代码库路径: {self.codebase_dir}")
        print(f"扫描文件数: {len(self.python_files)}")

        self.check_state_hex_compliance()
        self.check_moneyflow_compliance()
        self.check_semantic_compliance()
        self.check_pipeline_order()
        self.check_importability()

        return self.generate_report()

    def generate_report(self) -> Dict:
        """生成验证报告"""
        report = {
            "total_files": len(self.python_files),
            "total_violations": len(self.violations),
            "critical": 0,
            "error": 0,
            "warning": 0,
            "info": 0,
            "violations": [],
            "passed": len(self.violations) == 0,
        }

        for v in self.violations:
            report[v.level.value.lower()] += 1
            report["violations"].append({
                "level": v.level.value,
                "rule": v.rule,
                "file": v.file,
                "line": v.line,
                "message": v.message,
                "suggestion": v.suggestion,
            })

        return report

    def print_report(self, report: Dict):
        """打印报告"""
        print("\n" + "=" * 70)
        print("验证报告")
        print("=" * 70)

        print(f"\n扫描文件: {report['total_files']}")
        print(f"违规总数: {report['total_violations']}")
        print(f"  CRITICAL: {report['critical']}")
        print(f"  ERROR:    {report['error']}")
        print(f"  WARNING:  {report['warning']}")
        print(f"  INFO:     {report['info']}")

        if report['violations']:
            print("\n违规详情:")
            for i, v in enumerate(report['violations'], 1):
                print(f"\n  [{i}] [{v['level']}] {v['rule']}")
                if v['file']:
                    print(f"      位置: {v['file']}:{v['line']}")
                print(f"      问题: {v['message']}")
                if v['suggestion']:
                    print(f"      建议: {v['suggestion']}")
        else:
            print("\n未发现违规，所有检查通过！")

        print("\n" + "=" * 70)
        if report['passed']:
            print("结果: 通过")
        elif report['critical'] > 0:
            print("结果: 未通过（存在CRITICAL级别违规）")
        elif report['error'] > 0:
            print("结果: 未通过（存在ERROR级别违规）")
        else:
            print("结果: 通过（仅有WARNING/INFO）")
        print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description='P107/P106 合规验证')
    parser.add_argument('--codebase-dir', default=None,
                        help='代码库根目录（默认：上级目录的python/）')
    parser.add_argument('--verbose', action='store_true', help='详细输出')
    args = parser.parse_args()

    # 确定代码库路径
    if args.codebase_dir:
        codebase_dir = args.codebase_dir
    else:
        # 脚本在 scripts/ 下，代码库在 ../python/
        script_dir = Path(__file__).parent.resolve()
        codebase_dir = script_dir.parent / "python"

    verifier = P107P106Verifier(str(codebase_dir), verbose=args.verbose)
    report = verifier.run_all_checks()
    verifier.print_report(report)

    # 返回退出码
    if report['critical'] > 0 or report['error'] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
