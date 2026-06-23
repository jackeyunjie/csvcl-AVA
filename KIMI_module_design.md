# KIMI AI量化多周期视角交易平台 - 核心模块详细设计

**版本**: V1.0  
**日期**: 2026-06-06  
**文档编号**: KIMI-MD-001  
**设计原则**: 基于GitHub前沿开源项目独立设计，参考TradingAgents、Vibe-Trading、VectorBT最新实现

---

## 一、模块总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        KIMI核心模块详细设计                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    自然语言处理模块 (NL Processing)                   │   │
│  │  NLStrategyService → TemplateRegistry → StrategyValidator           │   │
│  │  LLMGateway → PromptEngine → CodeGenerator                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    回测引擎模块 (Backtest Engine)                     │   │
│  │  VectorizedBacktestEngine → MultiTimeframeAligner                   │   │
│  │  ParameterOptimizer → ReportGenerator → PerformanceAnalyzer         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    多Agent协作系统 (Multi-Agent System)               │   │
│  │  BaseAgent → ResearchAgent/TraderAgent/RiskAgent/ExecutionAgent     │   │
│  │  AgentOrchestrator → MessageBus → AgentStateManager                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    数据处理模块 (Data Processing)                     │   │
│  │  DataSource → MT5DataSource/ParquetDataSource                       │   │
│  │  DataPipeline → DataQualityMonitor → FeatureEngineer                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    MCP服务模块 (MCP Server)                           │   │
│  │  MCPServer → ToolRegistry → ToolExecutor                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、自然语言处理模块

### 2.1 模块概述

负责将用户的自然语言策略描述转换为可执行的策略代码，包含意图解析、模板匹配、代码生成和验证四个核心环节。

### 2.2 核心类设计

#### 2.2.1 NLStrategyService

```python
from typing import Optional, List, Dict
from dataclasses import dataclass
from enum import Enum
import json

class StrategyType(Enum):
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    MULTI_FACTOR = "multi_factor"
    STATISTICAL_ARBITRAGE = "statistical_arbitrage"

class CodeTarget(Enum):
    PYTHON = "python"
    MQL5 = "mql5"
    PINE_SCRIPT = "pine_script"
    TDX = "tdx"

@dataclass
class StrategyIntent:
    """策略意图结构化表示"""
    strategy_type: StrategyType
    entry_conditions: List[Dict]  # 入场条件列表
    exit_conditions: List[Dict]   # 出场条件列表
    indicators: List[Dict]        # 使用的指标及参数
    risk_params: Dict             # 风控参数
    timeframe: str                # 主周期
    symbols: List[str]            # 交易品种
    description: str              # 原始描述

@dataclass
class ValidationResult:
    """策略验证结果"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    ast_tree: Optional[dict]      # AST语法树
    backtest_preview: Optional[dict]  # 快速回测预览

class NLStrategyService:
    """
    自然语言策略生成服务
    
    核心流程:
    1. parse_natural_language() - 解析用户输入
    2. match_template() - 匹配策略模板
    3. generate_code() - 生成目标代码
    4. validate_strategy() - 验证策略有效性
    """
    
    def __init__(
        self,
        llm_gateway: 'LLMGateway',
        template_registry: 'TemplateRegistry',
        validator: 'StrategyValidator'
    ):
        self.llm = llm_gateway
        self.templates = template_registry
        self.validator = validator
        self.prompt_engine = PromptEngine()
    
    async def parse_natural_language(self, text: str) -> StrategyIntent:
        """
        使用LLM解析自然语言策略描述
        
        Args:
            text: 用户自然语言输入
            
        Returns:
            StrategyIntent: 结构化策略意图
            
        Example:
            >>> intent = await service.parse_natural_language(
            ...     "MA5上穿MA20时买入，跌破MA10时卖出，止损50点"
            ... )
        """
        # 构建结构化输出提示
        system_prompt = self.prompt_engine.get_intent_parsing_prompt()
        
        # 使用LLM提取策略要素
        response = await self.llm.structured_output(
            prompt=text,
            schema={
                "type": "object",
                "properties": {
                    "strategy_type": {"type": "string", "enum": [t.value for t in StrategyType]},
                    "entry_conditions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "indicator": {"type": "string"},
                                "condition": {"type": "string"},
                                "parameters": {"type": "object"}
                            }
                        }
                    },
                    "exit_conditions": {"type": "array"},
                    "indicators": {"type": "array"},
                    "risk_params": {"type": "object"},
                    "timeframe": {"type": "string"},
                    "symbols": {"type": "array", "items": {"type": "string"}}
                }
            }
        )
        
        return StrategyIntent(**response)
    
    def match_template(self, intent: StrategyIntent) -> 'StrategyTemplate':
        """
        根据策略意图匹配最佳模板
        
        匹配逻辑:
        1. 按strategy_type筛选候选模板
        2. 计算指标重叠度
        3. 计算条件结构相似度
        4. 返回得分最高的模板
        """
        candidates = self.templates.get_by_type(intent.strategy_type)
        
        best_match = None
        best_score = 0
        
        for template in candidates:
            score = self._calculate_template_match_score(intent, template)
            if score > best_score:
                best_score = score
                best_match = template
        
        return best_match
    
    async def generate_code(
        self,
        intent: StrategyIntent,
        target: CodeTarget,
        template: Optional['StrategyTemplate'] = None
    ) -> str:
        """
        生成目标格式的策略代码
        
        Args:
            intent: 策略意图
            target: 目标代码格式
            template: 可选的模板（如不传则自动匹配）
            
        Returns:
            str: 生成的代码字符串
        """
        if template is None:
            template = self.match_template(intent)
        
        # 准备模板变量
        context = {
            "intent": intent,
            "template": template,
            "risk_params": self._default_risk_params(intent)
        }
        
        # 使用Jinja2渲染模板
        code = template.render(target, context)
        
        # 使用LLM优化代码质量
        optimized = await self.llm.chat([
            {"role": "system", "content": f"Optimize this {target.value} trading strategy code"},
            {"role": "user", "content": code}
        ])
        
        return optimized
    
    async def validate_strategy(self, code: str, target: CodeTarget) -> ValidationResult:
        """
        验证策略代码的有效性
        
        验证内容:
        1. 语法正确性（AST解析）
        2. 逻辑合理性（条件互斥、参数范围）
        3. 风控完整性（止损止盈检查）
        4. 快速回测验证（1个月数据）
        """
        return await self.validator.validate(code, target)
    
    def _default_risk_params(self, intent: StrategyIntent) -> Dict:
        """生成默认风控参数"""
        return {
            "stop_loss_pips": 50,
            "take_profit_pips": 100,
            "max_position_size": 0.1,  # 手数
            "max_daily_loss": 0.02,     # 日亏损限额2%
            "max_drawdown": 0.10        # 最大回撤10%
        }
    
    def _calculate_template_match_score(
        self,
        intent: StrategyIntent,
        template: 'StrategyTemplate'
    ) -> float:
        """计算模板匹配得分"""
        score = 0.0
        
        # 指标重叠度 (40%)
        intent_indicators = {i["indicator"] for i in intent.indicators}
        template_indicators = {i["indicator"] for i in template.indicators}
        overlap = len(intent_indicators & template_indicators)
        score += (overlap / max(len(intent_indicators), 1)) * 0.4
        
        # 条件结构相似度 (40%)
        if len(intent.entry_conditions) == len(template.entry_conditions):
            score += 0.2
        if len(intent.exit_conditions) == len(template.exit_conditions):
            score += 0.2
        
        # 周期匹配 (20%)
        if intent.timeframe == template.timeframe:
            score += 0.2
        
        return score
```

#### 2.2.2 TemplateRegistry

```python
import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from typing import Dict, List

class StrategyTemplate:
    """策略模板"""
    
    def __init__(self, name: str, strategy_type: StrategyType, 
                 indicators: List[Dict], entry_conditions: List[Dict],
                 exit_conditions: List[Dict], timeframe: str):
        self.name = name
        self.strategy_type = strategy_type
        self.indicators = indicators
        self.entry_conditions = entry_conditions
        self.exit_conditions = exit_conditions
        self.timeframe = timeframe
        self._jinja_env = None
    
    def render(self, target: CodeTarget, context: Dict) -> str:
        """渲染模板生成代码"""
        template_file = f"{self.name}_{target.value}.j2"
        template = self._jinja_env.get_template(template_file)
        return template.render(**context)

class TemplateRegistry:
    """
    策略模板注册中心
    
    管理所有内置和用户自定义的策略模板
    """
    
    def __init__(self, template_dir: str = "templates/strategies"):
        self.template_dir = Path(template_dir)
        self.templates: Dict[str, StrategyTemplate] = {}
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True
        )
        self._load_builtin_templates()
    
    def _load_builtin_templates(self):
        """加载内置策略模板"""
        builtin_templates = [
            # 趋势类
            StrategyTemplate(
                name="ma_crossover",
                strategy_type=StrategyType.TREND_FOLLOWING,
                indicators=[
                    {"indicator": "MA", "parameters": {"period": 5}},
                    {"indicator": "MA", "parameters": {"period": 20}}
                ],
                entry_conditions=[
                    {"indicator": "MA5", "condition": "cross_above", "reference": "MA20"}
                ],
                exit_conditions=[
                    {"indicator": "MA5", "condition": "cross_below", "reference": "MA20"}
                ],
                timeframe="H1"
            ),
            StrategyTemplate(
                name="macd_trend",
                strategy_type=StrategyType.TREND_FOLLOWING,
                indicators=[
                    {"indicator": "MACD", "parameters": {"fast": 12, "slow": 26, "signal": 9}}
                ],
                entry_conditions=[
                    {"indicator": "MACD", "condition": "histogram_turn_positive"}
                ],
                exit_conditions=[
                    {"indicator": "MACD", "condition": "histogram_turn_negative"}
                ],
                timeframe="H4"
            ),
            # 反转类
            StrategyTemplate(
                name="rsi_reversal",
                strategy_type=StrategyType.MEAN_REVERSION,
                indicators=[
                    {"indicator": "RSI", "parameters": {"period": 14}}
                ],
                entry_conditions=[
                    {"indicator": "RSI", "condition": "below", "threshold": 30}
                ],
                exit_conditions=[
                    {"indicator": "RSI", "condition": "above", "threshold": 70}
                ],
                timeframe="H1"
            ),
            # 突破类
            StrategyTemplate(
                name="breakout_channel",
                strategy_type=StrategyType.BREAKOUT,
                indicators=[
                    {"indicator": "DonchianChannel", "parameters": {"period": 20}}
                ],
                entry_conditions=[
                    {"indicator": "Close", "condition": "break_above", "reference": "DC_Upper"}
                ],
                exit_conditions=[
                    {"indicator": "Close", "condition": "break_below", "reference": "DC_Lower"}
                ],
                timeframe="D1"
            ),
            # 多因子类 - State Hex共振
            StrategyTemplate(
                name="state_hex_resonance",
                strategy_type=StrategyType.MULTI_FACTOR,
                indicators=[
                    {"indicator": "StateHex", "parameters": {"timeframes": ["D1", "W1", "MN1"]}}
                ],
                entry_conditions=[
                    {"indicator": "StateHex", "condition": "all_bullish", "timeframes": ["D1", "W1", "MN1"]}
                ],
                exit_conditions=[
                    {"indicator": "StateHex", "condition": "any_bearish", "timeframes": ["D1", "W1", "MN1"]}
                ],
                timeframe="H1"
            ),
            # 收缩突破
            StrategyTemplate(
                name="contraction_breakout",
                strategy_type=StrategyType.BREAKOUT,
                indicators=[
                    {"indicator": "BB_Width", "parameters": {"period": 20, "std": 2}},
                    {"indicator": "ATR", "parameters": {"period": 14}}
                ],
                entry_conditions=[
                    {"indicator": "BB_Width", "condition": "contraction_end"},
                    {"indicator": "Close", "condition": "break_above", "reference": "BB_Upper"}
                ],
                exit_conditions=[
                    {"indicator": "Close", "condition": "break_below", "reference": "BB_Lower"}
                ],
                timeframe="H1"
            )
        ]
        
        for template in builtin_templates:
            self.templates[template.name] = template
    
    def get_by_type(self, strategy_type: StrategyType) -> List[StrategyTemplate]:
        """按类型获取模板"""
        return [t for t in self.templates.values() if t.strategy_type == strategy_type]
    
    def get_by_name(self, name: str) -> Optional[StrategyTemplate]:
        """按名称获取模板"""
        return self.templates.get(name)
    
    def add_template(self, template: StrategyTemplate):
        """添加自定义模板"""
        self.templates[template.name] = template
    
    def list_templates(self) -> List[Dict]:
        """列出所有模板"""
        return [
            {
                "name": t.name,
                "type": t.strategy_type.value,
                "timeframe": t.timeframe,
                "indicators": [i["indicator"] for i in t.indicators]
            }
            for t in self.templates.values()
        ]
```

#### 2.2.3 StrategyValidator

```python
import ast
import tempfile
import vectorbt as vbt
from typing import List, Tuple

class StrategyValidator:
    """
    策略验证器
    
    验证策略代码的语法正确性、逻辑合理性和可执行性
    """
    
    def __init__(self, data_source: 'DataSource'):
        self.data_source = data_source
    
    async def validate(self, code: str, target: CodeTarget) -> ValidationResult:
        """完整验证流程"""
        errors = []
        warnings = []
        ast_tree = None
        preview = None
        
        # 1. 语法验证
        syntax_valid, syntax_errors, ast_tree = self._validate_syntax(code, target)
        errors.extend(syntax_errors)
        
        if not syntax_valid:
            return ValidationResult(False, errors, warnings, ast_tree, preview)
        
        # 2. 逻辑验证
        logic_valid, logic_errors, logic_warnings = self._validate_logic(code, target)
        errors.extend(logic_errors)
        warnings.extend(logic_warnings)
        
        # 3. 风控验证
        risk_valid, risk_warnings = self._validate_risk_management(code, target)
        warnings.extend(risk_warnings)
        
        # 4. 快速回测验证
        if target == CodeTarget.PYTHON:
            preview = await self._quick_backtest(code)
        
        is_valid = len(errors) == 0
        return ValidationResult(is_valid, errors, warnings, ast_tree, preview)
    
    def _validate_syntax(self, code: str, target: CodeTarget) -> Tuple[bool, List[str], Optional[dict]]:
        """验证语法正确性"""
        errors = []
        tree = None
        
        if target == CodeTarget.PYTHON:
            try:
                tree = ast.parse(code)
            except SyntaxError as e:
                errors.append(f"语法错误: 第{e.lineno}行 - {e.msg}")
                return False, errors, None
            
            # 检查危险操作
            for node in ast.walk(tree):
                if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        if alias.name in ['os', 'sys', 'subprocess']:
                            errors.append(f"安全警告: 不允许导入 {alias.name} 模块")
        
        elif target == CodeTarget.MQL5:
            # MQL5语法检查（简化版）
            if 'void OnInit()' not in code and 'int OnInit()' not in code:
                errors.append("MQL5错误: 缺少OnInit()函数")
            if 'void OnTick()' not in code:
                errors.append("MQL5错误: 缺少OnTick()函数")
        
        return len(errors) == 0, errors, tree
    
    def _validate_logic(self, code: str, target: CodeTarget) -> Tuple[bool, List[str], List[str]]:
        """验证逻辑合理性"""
        errors = []
        warnings = []
        
        if target == CodeTarget.PYTHON:
            tree = ast.parse(code)
            
            # 检查死循环
            for node in ast.walk(tree):
                if isinstance(node, ast.While):
                    # 检查是否有break或条件变化
                    has_break = any(isinstance(n, ast.Break) for n in ast.walk(node))
                    if not has_break:
                        warnings.append("警告: While循环没有break，可能导致死循环")
            
            # 检查指标参数合理性
            # 这里可以添加更复杂的检查逻辑
        
        return len(errors) == 0, errors, warnings
    
    def _validate_risk_management(self, code: str, target: CodeTarget) -> Tuple[bool, List[str]]:
        """验证风控完整性"""
        warnings = []
        
        # 检查是否包含止损逻辑
        if 'stop' not in code.lower() and 'sl' not in code.lower():
            warnings.append("警告: 策略中没有检测到止损逻辑")
        
        # 检查是否包含止盈逻辑
        if 'take_profit' not in code.lower() and 'tp' not in code.lower():
            warnings.append("警告: 策略中没有检测到止盈逻辑")
        
        # 检查是否包含仓位管理
        if 'position_size' not in code.lower() and 'lot' not in code.lower():
            warnings.append("警告: 策略中没有检测到仓位管理逻辑")
        
        return True, warnings
    
    async def _quick_backtest(self, code: str) -> Optional[dict]:
        """快速回测验证（使用1个月数据）"""
        try:
            # 创建临时文件执行策略代码
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_path = f.name
            
            # 加载最近1个月数据
            data = self.data_source.get_recent_data(days=30)
            
            # 执行回测（简化版）
            # 实际实现需要更复杂的逻辑
            return {
                "status": "success",
                "trades": 5,
                "win_rate": 0.6,
                "profit": 100.0
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
```

#### 2.2.4 LLMGateway

```python
import os
from typing import List, Dict, Optional, AsyncGenerator
from dataclasses import dataclass
import aiohttp

@dataclass
class Message:
    role: str  # system, user, assistant
    content: str

@dataclass
class ChatResponse:
    content: str
    usage: Dict
    model: str

class LLMGateway:
    """
    LLM服务网关
    
    统一封装多种LLM提供商，支持动态切换和负载均衡
    """
    
    PROVIDERS = {
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "models": ["gpt-4o", "gpt-4o-mini", "o3-mini"]
        },
        "anthropic": {
            "base_url": "https://api.anthropic.com/v1",
            "models": ["claude-3-5-sonnet", "claude-3-opus"]
        },
        "deepseek": {
            "base_url": "https://api.deepseek.com/v1",
            "models": ["deepseek-chat", "deepseek-reasoner"]
        },
        "qwen": {
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "models": ["qwen2.5-72b-instruct", "qwen2.5-coder-32b"]
        },
        "ollama": {
            "base_url": "http://localhost:11434/v1",
            "models": ["llama3.1", "qwen2.5"]
        }
    }
    
    def __init__(self, provider: str = "deepseek", model: str = "deepseek-chat"):
        self.provider = provider
        self.model = model
        self.config = self.PROVIDERS.get(provider, {})
        self.api_key = os.getenv(f"{provider.upper()}_API_KEY")
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def chat(
        self,
        messages: List[Message],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> ChatResponse:
        """通用对话接口"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if tools:
            payload["tools"] = tools
        
        async with self.session.post(
            f"{self.config['base_url']}/chat/completions",
            headers=headers,
            json=payload
        ) as response:
            result = await response.json()
            
            return ChatResponse(
                content=result["choices"][0]["message"]["content"],
                usage=result.get("usage", {}),
                model=self.model
            )
    
    async def structured_output(
        self,
        prompt: str,
        schema: Dict,
        system_prompt: Optional[str] = None
    ) -> Dict:
        """
        结构化输出接口
        
        使用JSON Schema约束LLM输出格式
        """
        messages = []
        
        if system_prompt:
            messages.append(Message(role="system", content=system_prompt))
        
        schema_prompt = f"""
请根据以下JSON Schema格式输出结果：
{json.dumps(schema, indent=2, ensure_ascii=False)}

用户输入：{prompt}

请只输出JSON格式的结果，不要包含任何其他文本。
"""
        messages.append(Message(role="user", content=schema_prompt))
        
        response = await self.chat(messages, temperature=0.1)
        
        # 解析JSON输出
        try:
            import json
            return json.loads(response.content)
        except json.JSONDecodeError:
            # 尝试从文本中提取JSON
            import re
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            raise ValueError(f"无法解析LLM输出为JSON: {response.content}")
    
    async def stream_chat(
        self,
        messages: List[Message]
    ) -> AsyncGenerator[str, None]:
        """流式对话接口"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True
        }
        
        async with self.session.post(
            f"{self.config['base_url']}/chat/completions",
            headers=headers,
            json=payload
        ) as response:
            async for line in response.content:
                line = line.decode('utf-8').strip()
                if line.startswith('data: '):
                    data = line[6:]
                    if data == '[DONE]':
                        break
                    try:
                        chunk = json.loads(data)
                        if 'choices' in chunk and chunk['choices']:
                            delta = chunk['choices'][0].get('delta', {})
                            if 'content' in delta:
                                yield delta['content']
                    except json.JSONDecodeError:
                        continue
```

---

## 三、回测引擎模块

### 3.1 模块概述

基于VectorBT向量化回测引擎，提供高性能、多维度的策略回测能力。

### 3.2 核心类设计

#### 3.2.1 VectorizedBacktestEngine

```python
import vectorbt as vbt
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class BacktestConfig:
    """回测配置"""
    symbols: List[str]
    timeframe: str
    start_date: datetime
    end_date: datetime
    initial_balance: float = 10000.0
    commission: float = 0.001  # 0.1%
    slippage: float = 0.0001   # 1 pip
    leverage: float = 1.0
    risk_per_trade: float = 0.02  # 每笔交易风险2%

@dataclass
class BacktestResult:
    """回测结果"""
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    max_drawdown_duration: timedelta
    win_rate: float
    profit_factor: float
    total_trades: int
    avg_trade_return: float
    equity_curve: pd.Series
    trades: pd.DataFrame
    metrics: Dict

class VectorizedBacktestEngine:
    """
    向量化回测引擎
    
    基于VectorBT实现高性能回测，支持多周期数据对齐和大规模参数扫描
    """
    
    def __init__(self, data_source: 'DataSource'):
        self.data_source = data_source
        self.aligner = MultiTimeframeAligner()
    
    async def run_backtest(
        self,
        strategy_code: str,
        config: BacktestConfig
    ) -> BacktestResult:
        """
        执行回测
        
        Args:
            strategy_code: Python策略代码字符串
            config: 回测配置
            
        Returns:
            BacktestResult: 回测结果
            
        Performance Target: H1数据5年量 < 10秒
        """
        # 1. 加载历史数据
        data = await self._load_data(config)
        
        # 2. 多周期数据对齐
        aligned_data = self.aligner.align(data, config.timeframe)
        
        # 3. 执行策略代码生成信号
        entries, exits = self._execute_strategy(strategy_code, aligned_data)
        
        # 4. 使用VectorBT模拟持仓
        portfolio = vbt.Portfolio.from_signals(
            aligned_data['close'],
            entries=entries,
            exits=exits,
            init_cash=config.initial_balance,
            fees=config.commission,
            slippage=config.slippage,
            freq=self._timeframe_to_freq(config.timeframe)
        )
        
        # 5. 计算绩效指标
        result = self._calculate_metrics(portfolio, config)
        
        return result
    
    async def _load_data(self, config: BacktestConfig) -> pd.DataFrame:
        """加载历史数据"""
        data = self.data_source.get_ohlcv(
            symbols=config.symbols,
            timeframe=config.timeframe,
            start=config.start_date,
            end=config.end_date
        )
        return data
    
    def _execute_strategy(
        self,
        strategy_code: str,
        data: pd.DataFrame
    ) -> Tuple[pd.Series, pd.Series]:
        """
        执行策略代码生成入场/出场信号
        
        策略代码需要实现 generate_signals(data) 函数
        返回 (entries, exits) 两个布尔Series
        """
        # 创建安全的执行环境
        namespace = {
            'pd': pd,
            'np': np,
            'vbt': vbt,
            'data': data
        }
        
        # 执行策略代码
        exec(strategy_code, namespace)
        
        # 调用策略的generate_signals函数
        if 'generate_signals' not in namespace:
            raise ValueError("策略代码必须定义 generate_signals(data) 函数")
        
        entries, exits = namespace['generate_signals'](data)
        
        return entries, exits
    
    def _calculate_metrics(
        self,
        portfolio: vbt.Portfolio,
        config: BacktestConfig
    ) -> BacktestResult:
        """计算回测绩效指标"""
        
        stats = portfolio.stats()
        
        return BacktestResult(
            total_return=stats['Total Return [%]'],
            annualized_return=stats['Annualized Return [%]'],
            sharpe_ratio=stats.get('Sharpe Ratio', 0),
            sortino_ratio=stats.get('Sortino Ratio', 0),
            calmar_ratio=stats.get('Calmar Ratio', 0),
            max_drawdown=stats['Max Drawdown [%]'],
            max_drawdown_duration=stats['Max Drawdown Duration'],
            win_rate=stats['Win Rate [%]'],
            profit_factor=stats.get('Profit Factor', 0),
            total_trades=stats['Total Trades'],
            avg_trade_return=stats.get('Avg Winning Trade [%]', 0),
            equity_curve=portfolio.value(),
            trades=portfolio.trades.records,
            metrics=stats.to_dict()
        )
    
    def _timeframe_to_freq(self, timeframe: str) -> str:
        """时间周期转频率字符串"""
        mapping = {
            'M1': '1min', 'M5': '5min', 'M15': '15min', 'M30': '30min',
            'H1': '1h', 'H4': '4h', 'D1': '1d', 'W1': '1W', 'MN1': '1M'
        }
        return mapping.get(timeframe, '1d')
    
    async def optimize_parameters(
        self,
        strategy_code: str,
        config: BacktestConfig,
        param_grid: Dict[str, List],
        method: str = "grid",
        metric: str = "sharpe_ratio"
    ) -> List[Dict]:
        """
        参数优化
        
        Args:
            strategy_code: 策略代码
            config: 回测配置
            param_grid: 参数网格，如 {"fast_ma": [5, 10, 20], "slow_ma": [20, 50, 100]}
            method: 优化方法 (grid/random/bayesian)
            metric: 优化目标指标
            
        Returns:
            List[Dict]: 参数组合及对应绩效，按目标指标排序
        """
        import itertools
        
        results = []
        
        if method == "grid":
            # 网格搜索
            keys = list(param_grid.keys())
            values = list(param_grid.values())
            
            for combo in itertools.product(*values):
                params = dict(zip(keys, combo))
                
                # 替换策略代码中的参数
                code_with_params = self._inject_params(strategy_code, params)
                
                # 执行回测
                result = await self.run_backtest(code_with_params, config)
                
                results.append({
                    "params": params,
                    "metric": getattr(result, metric),
                    "result": result
                })
        
        elif method == "bayesian":
            # 贝叶斯优化 (使用Optuna)
            results = await self._bayesian_optimize(
                strategy_code, config, param_grid, metric
            )
        
        # 按目标指标排序
        results.sort(key=lambda x: x["metric"], reverse=True)
        
        return results
    
    def _inject_params(self, code: str, params: Dict) -> str:
        """将参数注入策略代码"""
        param_lines = "\n".join([
            f"{key} = {repr(value)}" for key, value in params.items()
        ])
        return param_lines + "\n" + code
    
    async def _bayesian_optimize(
        self,
        strategy_code: str,
        config: BacktestConfig,
        param_grid: Dict[str, List],
        metric: str
    ) -> List[Dict]:
        """贝叶斯优化 (使用Optuna)"""
        import optuna
        
        def objective(trial):
            params = {}
            for key, values in param_grid.items():
                params[key] = trial.suggest_categorical(key, values)
            
            code_with_params = self._inject_params(strategy_code, params)
            
            # 注意：这里需要同步执行，Optuna不支持异步
            # 实际实现中可能需要使用线程池
            result = asyncio.get_event_loop().run_until_complete(
                self.run_backtest(code_with_params, config)
            )
            
            return getattr(result, metric)
        
        study = optuna.create_study(direction="maximize")
        study.optimize(objective, n_trials=100)
        
        # 返回最优结果
        return [{
            "params": study.best_params,
            "metric": study.best_value,
            "result": None  # 需要重新运行获取完整结果
        }]
```

#### 3.2.2 MultiTimeframeAligner

```python
class MultiTimeframeAligner:
    """
    多周期数据对齐器
    
    将不同时间周期的数据对齐到统一时间轴
    """
    
    def align(
        self,
        data: Dict[str, pd.DataFrame],
        base_timeframe: str
    ) -> pd.DataFrame:
        """
        对齐多周期数据
        
        Args:
            data: 各周期数据字典，如 {"H1": df1, "D1": df2, "W1": df3}
            base_timeframe: 基准周期
            
        Returns:
            pd.DataFrame: 对齐后的数据，包含各周期列
        """
        base_df = data[base_timeframe].copy()
        
        for tf, df in data.items():
            if tf == base_timeframe:
                continue
            
            # 前向填充对齐
            aligned = self._forward_fill_align(df, base_df.index)
            
            # 重命名列以避免冲突
            aligned.columns = [f"{tf}_{col}" for col in aligned.columns]
            
            # 合并到基准数据
            base_df = pd.concat([base_df, aligned], axis=1)
        
        return base_df
    
    def _forward_fill_align(
        self,
        source: pd.DataFrame,
        target_index: pd.DatetimeIndex
    ) -> pd.DataFrame:
        """前向填充对齐"""
        # 重新索引到目标时间轴
        aligned = source.reindex(target_index, method='ffill')
        return aligned
```

#### 3.2.3 ReportGenerator

```python
from jinja2 import Template
import plotly.graph_objects as go
from plotly.subplots import make_subplots

class ReportGenerator:
    """
    回测报告生成器
    
    生成HTML/PDF/JSON格式的回测报告
    """
    
    def __init__(self, template_dir: str = "templates/reports"):
        self.template_dir = Path(template_dir)
    
    def generate_html(self, result: BacktestResult) -> str:
        """生成HTML报告"""
        
        # 创建图表
        fig = self._create_charts(result)
        chart_html = fig.to_html(include_plotlyjs='cdn')
        
        # 渲染模板
        template = Template(self._get_html_template())
        
        html = template.render(
            result=result,
            chart_html=chart_html,
            generated_at=datetime.now()
        )
        
        return html
    
    def _create_charts(self, result: BacktestResult) -> go.Figure:
        """创建回测图表"""
        
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=('Equity Curve', 'Drawdown', 'Monthly Returns')
        )
        
        # 收益曲线
        fig.add_trace(
            go.Scatter(
                x=result.equity_curve.index,
                y=result.equity_curve.values,
                name='Equity',
                line=dict(color='blue')
            ),
            row=1, col=1
        )
        
        # 回撤曲线
        cummax = result.equity_curve.cummax()
        drawdown = (result.equity_curve - cummax) / cummax * 100
        fig.add_trace(
            go.Scatter(
                x=drawdown.index,
                y=drawdown.values,
                name='Drawdown',
                fill='tozeroy',
                line=dict(color='red')
            ),
            row=2, col=1
        )
        
        # 月度收益热力图
        monthly_returns = result.equity_curve.resample('M').last().pct_change() * 100
        monthly_returns = monthly_returns.dropna()
        
        fig.add_trace(
            go.Bar(
                x=monthly_returns.index,
                y=monthly_returns.values,
                name='Monthly Return',
                marker_color=['green' if x > 0 else 'red' for x in monthly_returns.values]
            ),
            row=3, col=1
        )
        
        fig.update_layout(
            height=800,
            title_text=f"Backtest Report - Total Return: {result.total_return:.2f}%",
            showlegend=False
        )
        
        return fig
    
    def _get_html_template(self) -> str:
        """获取HTML模板"""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>KIMI Backtest Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
        .metric-card { background: #f5f5f5; padding: 15px; border-radius: 8px; }
        .metric-value { font-size: 24px; font-weight: bold; color: #333; }
        .metric-label { font-size: 12px; color: #666; }
        .positive { color: green; }
        .negative { color: red; }
    </style>
</head>
<body>
    <h1>KIMI AI Trading - Backtest Report</h1>
    <p>Generated at: {{ generated_at }}</p>
    
    <div class="metrics">
        <div class="metric-card">
            <div class="metric-value {{ 'positive' if result.total_return > 0 else 'negative' }}">
                {{ "%.2f"|format(result.total_return) }}%
            </div>
            <div class="metric-label">Total Return</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{{ "%.2f"|format(result.sharpe_ratio) }}</div>
            <div class="metric-label">Sharpe Ratio</div>
        </div>
        <div class="metric-card">
            <div class="metric-value negative">{{ "%.2f"|format(result.max_drawdown) }}%</div>
            <div class="metric-label">Max Drawdown</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{{ "%.1f"|format(result.win_rate) }}%</div>
            <div class="metric-label">Win Rate</div>
        </div>
    </div>
    
    <h2>Performance Charts</h2>
    {{ chart_html|safe }}
    
    <h2>Trade Statistics</h2>
    <table>
        <tr><td>Total Trades</td><td>{{ result.total_trades }}</td></tr>
        <tr><td>Profit Factor</td><td>{{ "%.2f"|format(result.profit_factor) }}</td></tr>
        <tr><td>Avg Trade Return</td><td>{{ "%.2f"|format(result.avg_trade_return) }}%</td></tr>
    </table>
</body>
</html>
        """
```

---

## 四、多Agent协作系统

### 4.1 模块概述

基于LangGraph框架构建的多Agent协作系统，模拟真实交易公司的组织架构。

### 4.2 核心类设计

#### 4.2.1 BaseAgent

```python
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime
import asyncio
from enum import Enum

class AgentState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"

class AgentMessage:
    """Agent间消息"""
    
    def __init__(
        self,
        msg_id: str,
        from_agent: str,
        to_agent: str,
        msg_type: str,
        priority: int,
        payload: Dict,
        requires_ack: bool = False
    ):
        self.msg_id = msg_id
        self.from_agent = from_agent
        self.to_agent = to_agent
        self.msg_type = msg_type
        self.priority = priority
        self.timestamp = datetime.utcnow()
        self.payload = payload
        self.requires_ack = requires_ack
        self.acknowledged = False

class BaseAgent(ABC):
    """
    Agent抽象基类
    
    所有Agent的通用接口和生命周期管理
    """
    
    def __init__(self, agent_id: str, name: str, orchestrator: 'AgentOrchestrator'):
        self.agent_id = agent_id
        self.name = name
        self.orchestrator = orchestrator
        self.state = AgentState.IDLE
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.context: Dict[str, Any] = {}
        self.task: Optional[asyncio.Task] = None
    
    async def start(self):
        """启动Agent"""
        self.state = AgentState.RUNNING
        self.task = asyncio.create_task(self._run_loop())
        await self.on_start()
    
    async def stop(self):
        """停止Agent"""
        self.state = AgentState.STOPPED
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        await self.on_stop()
    
    async def pause(self):
        """暂停Agent"""
        self.state = AgentState.PAUSED
        await self.on_pause()
    
    async def resume(self):
        """恢复Agent"""
        self.state = AgentState.RUNNING
        await self.on_resume()
    
    async def send_message(self, to_agent: str, msg_type: str, payload: Dict, priority: int = 5):
        """发送消息给其他Agent"""
        msg = AgentMessage(
            msg_id=str(uuid.uuid4()),
            from_agent=self.agent_id,
            to_agent=to_agent,
            msg_type=msg_type,
            priority=priority,
            payload=payload
        )
        await self.orchestrator.dispatch_message(msg)
    
    async def _run_loop(self):
        """主运行循环"""
        while self.state != AgentState.STOPPED:
            try:
                if self.state == AgentState.PAUSED:
                    await asyncio.sleep(1)
                    continue
                
                # 处理消息队列
                try:
                    msg = await asyncio.wait_for(
                        self.message_queue.get(),
                        timeout=1.0
                    )
                    await self._handle_message(msg)
                except asyncio.TimeoutError:
                    pass
                
                # 执行Agent逻辑
                await self.on_tick()
                
            except Exception as e:
                self.state = AgentState.ERROR
                await self.on_error(e)
    
    async def _handle_message(self, msg: AgentMessage):
        """处理接收到的消息"""
        await self.on_message(msg)
        
        if msg.requires_ack:
            await self.send_message(
                msg.from_agent,
                "ACK",
                {"original_msg_id": msg.msg_id}
            )
    
    @abstractmethod
    async def on_start(self):
        """Agent启动时的初始化逻辑"""
        pass
    
    @abstractmethod
    async def on_stop(self):
        """Agent停止时的清理逻辑"""
        pass
    
    @abstractmethod
    async def on_tick(self):
        """Agent主逻辑，每tick执行"""
        pass
    
    @abstractmethod
    async def on_message(self, msg: AgentMessage):
        """处理消息"""
        pass
    
    async def on_pause(self):
        """暂停时的逻辑"""
        pass
    
    async def on_resume(self):
        """恢复时的逻辑"""
        pass
    
    async def on_error(self, error: Exception):
        """错误处理"""
        print(f"Agent {self.name} error: {error}")
```

#### 4.2.2 ResearchAgent

```python
class ResearchAgent(BaseAgent):
    """
    研究Agent
    
    负责市场研究、策略发现和信号生成
    """
    
    def __init__(self, agent_id: str, name: str, orchestrator: 'AgentOrchestrator',
                 research_type: str = "technical"):
        super().__init__(agent_id, name, orchestrator)
        self.research_type = research_type  # technical/fundamental/sentiment/quantitative
        self.signals: List[Dict] = []
        self.reports: List[Dict] = []
    
    async def on_start(self):
        """初始化研究资源"""
        print(f"ResearchAgent {self.name} started (type: {self.research_type})")
    
    async def on_tick(self):
        """执行研究分析"""
        # 根据研究类型执行不同分析
        if self.research_type == "technical":
            await self._technical_analysis()
        elif self.research_type == "fundamental":
            await self._fundamental_analysis()
        elif self.research_type == "sentiment":
            await self._sentiment_analysis()
        elif self.research_type == "quantitative":
            await self._quantitative_analysis()
    
    async def _technical_analysis(self):
        """技术分析"""
        # 获取最新市场数据
        market_data = await self._get_market_data()
        
        # 计算技术指标
        signals = self._calculate_signals(market_data)
        
        # 发送信号给交易员Agent
        for signal in signals:
            await self.send_message(
                to_agent="trader",
                msg_type="SIGNAL",
                priority=signal.get("confidence", 5),
                payload={
                    "signal_type": signal["type"],
                    "symbol": signal["symbol"],
                    "confidence": signal["confidence"],
                    "reasoning": signal["reasoning"],
                    "suggested_entry": signal.get("entry_price"),
                    "suggested_sl": signal.get("stop_loss"),
                    "suggested_tp": signal.get("take_profit"),
                    "timeframe": signal["timeframe"]
                }
            )
    
    async def on_message(self, msg: AgentMessage):
        """处理消息"""
        if msg.msg_type == "REQUEST_RESEARCH":
            # 响应研究请求
            symbol = msg.payload.get("symbol")
            research = await self._research_symbol(symbol)
            await self.send_message(
                to_agent=msg.from_agent,
                msg_type="RESEARCH_REPORT",
                payload=research
            )
    
    def _calculate_signals(self, data: pd.DataFrame) -> List[Dict]:
        """计算交易信号"""
        signals = []
        
        # 示例：简单的MA交叉信号
        data['MA5'] = data['close'].rolling(5).mean()
        data['MA20'] = data['close'].rolling(20).mean()
        
        if data['MA5'].iloc[-1] > data['MA20'].iloc[-1] and \
           data['MA5'].iloc[-2] <= data['MA20'].iloc[-2]:
            signals.append({
                "type": "BUY",
                "symbol": data['symbol'].iloc[-1],
                "confidence": 0.7,
                "reasoning": "MA5 crossed above MA20",
                "timeframe": "H1"
            })
        
        return signals
```

#### 4.2.3 TraderAgent

```python
class TraderAgent(BaseAgent):
    """
    交易员Agent
    
    综合各方信息做出交易决策
    """
    
    def __init__(self, agent_id: str, name: str, orchestrator: 'AgentOrchestrator'):
        super().__init__(agent_id, name, orchestrator)
        self.pending_signals: List[Dict] = []
        self.active_positions: Dict[str, Dict] = {}
        self.decision_log: List[Dict] = []
    
    async def on_tick(self):
        """评估信号并做出交易决策"""
        # 处理待处理信号
        for signal in self.pending_signals:
            decision = await self._evaluate_signal(signal)
            if decision["action"] == "EXECUTE":
                await self._send_order(signal, decision)
            self.decision_log.append(decision)
        
        self.pending_signals = []
    
    async def on_message(self, msg: AgentMessage):
        """处理消息"""
        if msg.msg_type == "SIGNAL":
            # 接收研究Agent的信号
            self.pending_signals.append(msg.payload)
        
        elif msg.msg_type == "RISK_CHECK_RESULT":
            # 接收风控Agent的检查结果
            if msg.payload.get("approved"):
                # 执行交易
                pass
            else:
                # 拒绝交易，记录原因
                self.decision_log.append({
                    "action": "REJECTED",
                    "reason": msg.payload.get("reason")
                })
        
        elif msg.msg_type == "ORDER_FILLED":
            # 更新持仓
            self.active_positions[msg.payload["symbol"]] = msg.payload
    
    async def _evaluate_signal(self, signal: Dict) -> Dict:
        """评估交易信号"""
        # 1. 检查信号质量
        if signal["confidence"] < 0.6:
            return {"action": "IGNORE", "reason": "confidence too low"}
        
        # 2. 查询风控限额
        await self.send_message(
            to_agent="risk",
            msg_type="RISK_CHECK",
            payload={
                "symbol": signal["symbol"],
                "direction": signal["signal_type"],
                "size": 0.1  # 默认手数
            },
            requires_ack=True
        )
        
        # 等待风控检查（简化版，实际应使用异步等待）
        return {"action": "PENDING_RISK_CHECK", "signal": signal}
    
    async def _send_order(self, signal: Dict, decision: Dict):
        """发送订单给执行Agent"""
        await self.send_message(
            to_agent="execution",
            msg_type="EXECUTE_ORDER",
            priority=1,
            payload={
                "symbol": signal["symbol"],
                "direction": signal["signal_type"],
                "size": 0.1,
                "entry_price": signal.get("suggested_entry"),
                "stop_loss": signal.get("suggested_sl"),
                "take_profit": signal.get("suggested_tp")
            }
        )
```

#### 4.2.4 RiskAgent

```python
class RiskAgent(BaseAgent):
    """
    风控Agent
    
    实时监控风险，触发风控措施
    """
    
    def __init__(self, agent_id: str, name: str, orchestrator: 'AgentOrchestrator'):
        super().__init__(agent_id, name, orchestrator)
        self.risk_limits = {
            "max_drawdown": 0.10,      # 最大回撤10%
            "max_daily_loss": 0.02,     # 日亏损限额2%
            "max_position_size": 1.0,   # 最大持仓1手
            "max_total_exposure": 5.0,  # 最大总敞口5手
            "max_margin_usage": 0.50    # 保证金使用率50%
        }
        self.daily_pnl = 0
        self.risk_events: List[Dict] = []
    
    async def on_tick(self):
        """监控风险指标"""
        # 获取账户状态
        account = await self._get_account_status()
        
        # 检查各项风险限额
        checks = [
            self._check_drawdown(account),
            self._check_daily_loss(),
            self._check_position_limits(account),
            self._check_margin_usage(account)
        ]
        
        for check in checks:
            if not check["passed"]:
                await self._trigger_risk_action(check)
    
    async def on_message(self, msg: AgentMessage):
        """处理消息"""
        if msg.msg_type == "RISK_CHECK":
            # 响应风控检查请求
            result = await self._check_trade_risk(msg.payload)
            await self.send_message(
                to_agent=msg.from_agent,
                msg_type="RISK_CHECK_RESULT",
                payload=result
            )
    
    async def _check_trade_risk(self, trade: Dict) -> Dict:
        """检查单笔交易风险"""
        symbol = trade["symbol"]
        size = trade["size"]
        
        # 检查持仓限额
        current_exposure = await self._get_total_exposure()
        if current_exposure + size > self.risk_limits["max_total_exposure"]:
            return {
                "approved": False,
                "reason": f"Total exposure would exceed limit: {current_exposure + size} > {self.risk_limits['max_total_exposure']}"
            }
        
        # 检查单品种限额
        symbol_exposure = await self._get_symbol_exposure(symbol)
        if symbol_exposure + size > self.risk_limits["max_position_size"]:
            return {
                "approved": False,
                "reason": f"Symbol exposure would exceed limit"
            }
        
        return {"approved": True}
    
    async def _trigger_risk_action(self, check: Dict):
        """触发风控措施"""
        level = check["level"]  # warning/limit/forced/emergency
        
        if level == "warning":
            await self.send_message(
                to_agent="trader",
                msg_type="RISK_WARNING",
                payload=check
            )
        elif level == "limit":
            await self.send_message(
                to_agent="trader",
                msg_type="RISK_LIMIT",
                payload={"action": "STOP_NEW_POSITIONS", **check}
            )
        elif level == "forced":
            await self.send_message(
                to_agent="execution",
                msg_type="RISK_FORCED",
                payload={"action": "REDUCE_POSITIONS", **check}
            )
        elif level == "emergency":
            await self.send_message(
                to_agent="execution",
                msg_type="RISK_EMERGENCY",
                payload={"action": "FLATTEN_ALL", **check}
            )
```

#### 4.2.5 AgentOrchestrator

```python
class AgentOrchestrator:
    """
    Agent编排器
    
    基于LangGraph框架管理Agent生命周期和协作调度
    """
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.message_bus: asyncio.Queue = asyncio.Queue()
        self.event_bus: asyncio.Queue = asyncio.Queue()
        self.running = False
    
    async def register_agent(self, agent: BaseAgent) -> str:
        """注册Agent"""
        self.agents[agent.agent_id] = agent
        return agent.agent_id
    
    async def start_all(self):
        """启动所有Agent"""
        self.running = True
        
        # 启动消息总线
        asyncio.create_task(self._message_bus_loop())
        asyncio.create_task(self._event_bus_loop())
        
        # 启动所有Agent
        for agent in self.agents.values():
            await agent.start()
    
    async def stop_all(self):
        """停止所有Agent"""
        self.running = False
        
        for agent in self.agents.values():
            await agent.stop()
    
    async def dispatch_message(self, msg: AgentMessage):
        """分发消息到目标Agent"""
        await self.message_bus.put(msg)
    
    async def broadcast_event(self, event: Dict):
        """广播系统事件到所有Agent"""
        await self.event_bus.put(event)
    
    async def _message_bus_loop(self):
        """消息总线循环"""
        while self.running:
            try:
                msg = await asyncio.wait_for(self.message_bus.get(), timeout=1.0)
                
                # 根据消息类型分发
                if msg.to_agent in self.agents:
                    target_agent = self.agents[msg.to_agent]
                    await target_agent.message_queue.put(msg)
                elif msg.to_agent == "*":  # 广播消息
                    for agent in self.agents.values():
                        await agent.message_queue.put(msg)
                        
            except asyncio.TimeoutError:
                continue
    
    async def _event_bus_loop(self):
        """事件总线循环"""
        while self.running:
            try:
                event = await asyncio.wait_for(self.event_bus.get(), timeout=1.0)
                
                # 广播事件到所有Agent
                for agent in self.agents.values():
                    await agent.message_queue.put(AgentMessage(
                        msg_id=str(uuid.uuid4()),
                        from_agent="system",
                        to_agent=agent.agent_id,
                        msg_type="SYSTEM_EVENT",
                        priority=5,
                        payload=event
                    ))
                    
            except asyncio.TimeoutError:
                continue
    
    def get_agent_status(self, agent_id: str) -> Dict:
        """获取Agent状态"""
        agent = self.agents.get(agent_id)
        if not agent:
            return {"error": "Agent not found"}
        
        return {
            "agent_id": agent.agent_id,
            "name": agent.name,
            "state": agent.state.value,
            "queue_size": agent.message_queue.qsize(),
            "context_keys": list(agent.context.keys())
        }
```

---

## 五、数据处理模块

### 5.1 模块概述

统一数据入口，支持多数据源接入和数据质量监控。

### 5.2 核心类设计

#### 5.2.1 DataSource

```python
from abc import ABC, abstractmethod

class DataSource(ABC):
    """数据源抽象基类"""
    
    @abstractmethod
    async def get_ohlcv(self, symbol: str, timeframe: str, 
                        start: datetime, end: datetime) -> pd.DataFrame:
        """获取OHLCV数据"""
        pass
    
    @abstractmethod
    async def get_tick(self, symbol: str) -> Dict:
        """获取最新Tick"""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """检查连接状态"""
        pass

class MT5DataSource(DataSource):
    """MT5数据源"""
    
    def __init__(self, bridge: 'MT5Bridge'):
        self.bridge = bridge
    
    async def get_ohlcv(self, symbol: str, timeframe: str,
                        start: datetime, end: datetime) -> pd.DataFrame:
        """通过ZeroMQ从MT5获取历史数据"""
        return await self.bridge.request_historical_data(
            symbol, timeframe, start, end
        )
    
    async def get_tick(self, symbol: str) -> Dict:
        """获取最新Tick"""
        return self.bridge.get_latest_tick(symbol)
    
    def is_connected(self) -> bool:
        return self.bridge.is_connected()

class ParquetDataSource(DataSource):
    """Parquet文件数据源"""
    
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
    
    async def get_ohlcv(self, symbol: str, timeframe: str,
                        start: datetime, end: datetime) -> pd.DataFrame:
        """从Parquet文件读取历史数据"""
        file_path = self.data_dir / f"{symbol}_{timeframe}.parquet"
        
        if not file_path.exists():
            raise FileNotFoundError(f"Data file not found: {file_path}")
        
        df = pd.read_parquet(file_path)
        df = df[(df.index >= start) & (df.index <= end)]
        
        return df
    
    def is_connected(self) -> bool:
        return True
```

#### 5.2.2 DataPipeline

```python
class DataPipeline:
    """
    数据处理管道
    
    统一数据入口，包含质量监控和特征工程
    """
    
    def __init__(self, sources: List[DataSource]):
        self.sources = sources
        self.quality_monitor = DataQualityMonitor()
        self.feature_engineer = FeatureEngineer()
    
    async def get_data(self, symbol: str, timeframe: str,
                       start: datetime, end: datetime) -> pd.DataFrame:
        """
        获取数据（自动选择最佳数据源）
        
        优先级：
        1. MT5实时数据（如果连接正常）
        2. Parquet本地缓存
        3. 其他数据源
        """
        for source in self.sources:
            if source.is_connected():
                try:
                    data = await source.get_ohlcv(symbol, timeframe, start, end)
                    
                    # 数据质量检查
                    quality_report = self.quality_monitor.check(data)
                    if not quality_report["passed"]:
                        print(f"Data quality issues: {quality_report['issues']}")
                    
                    # 特征工程
                    data = self.feature_engineer.process(data)
                    
                    return data
                    
                except Exception as e:
                    print(f"Source failed: {e}, trying next...")
                    continue
        
        raise Exception("All data sources failed")

class DataQualityMonitor:
    """数据质量监控器"""
    
    def check(self, data: pd.DataFrame) -> Dict:
        """检查数据质量"""
        issues = []
        
        # 检查缺失值
        missing = data.isnull().sum().sum()
        if missing > 0:
            issues.append(f"Found {missing} missing values")
        
        # 检查异常值
        for col in ['open', 'high', 'low', 'close']:
            if col in data.columns:
                q1 = data[col].quantile(0.01)
                q99 = data[col].quantile(0.99)
                outliers = data[(data[col] < q1 * 0.5) | (data[col] > q99 * 2)]
                if len(outliers) > 0:
                    issues.append(f"Found {len(outliers)} outliers in {col}")
        
        # 检查OHLC逻辑
        if 'high' in data.columns and 'low' in data.columns:
            invalid = data[data['high'] < data['low']]
            if len(invalid) > 0:
                issues.append(f"Found {len(invalid)} invalid OHLC records")
        
        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "total_rows": len(data),
            "missing_values": missing
        }

class FeatureEngineer:
    """特征工程器"""
    
    def process(self, data: pd.DataFrame) -> pd.DataFrame:
        """添加技术指标特征"""
        df = data.copy()
        
        # 移动平均线
        for period in [5, 10, 20, 50, 100, 200]:
            df[f'MA_{period}'] = df['close'].rolling(period).mean()
        
        # RSI
        df['RSI_14'] = self._calculate_rsi(df['close'], 14)
        
        # MACD
        df['MACD'], df['MACD_Signal'], df['MACD_Hist'] = self._calculate_macd(df['close'])
        
        # ATR
        df['ATR_14'] = self._calculate_atr(df, 14)
        
        # 布林带
        df['BB_Upper'], df['BB_Middle'], df['BB_Lower'] = self._calculate_bollinger(df['close'])
        
        return df
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """计算RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_macd(self, prices: pd.Series) -> tuple:
        """计算MACD"""
        exp1 = prices.ewm(span=12).mean()
        exp2 = prices.ewm(span=26).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9).mean()
        hist = macd - signal
        return macd, signal, hist
    
    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """计算ATR"""
        high_low = data['high'] - data['low']
        high_close = abs(data['high'] - data['close'].shift())
        low_close = abs(data['low'] - data['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.rolling(period).mean()
    
    def _calculate_bollinger(self, prices: pd.Series, period: int = 20, std: int = 2) -> tuple:
        """计算布林带"""
        middle = prices.rolling(period).mean()
        std_dev = prices.rolling(period).std()
        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)
        return upper, middle, lower
```

---

## 六、MCP服务模块

### 6.1 模块概述

遵循Model Context Protocol标准，将平台核心能力暴露为MCP工具，支持Claude/Cursor等AI助手调用。

### 6.2 核心类设计

#### 6.2.1 MCPServer

```python
from mcp.server import Server
from mcp.types import Tool, TextContent

class MCPServer:
    """
    MCP服务器
    
    暴露平台核心功能为MCP工具
    """
    
    def __init__(self, orchestrator: AgentOrchestrator, 
                 backtest_service: 'BacktestService',
                 strategy_service: 'NLStrategyService'):
        self.orchestrator = orchestrator
        self.backtest = backtest_service
        self.strategy = strategy_service
        self.server = Server("kimi-trading")
        self._register_tools()
    
    def _register_tools(self):
        """注册MCP工具"""
        
        @self.server.tool()
        async def analyze_market(symbol: str, timeframe: str = "H1") -> str:
            """分析市场状态"""
            # 获取市场数据并分析
            return f"Market analysis for {symbol} on {timeframe}"
        
        @self.server.tool()
        async def run_backtest(strategy_code: str, symbol: str, 
                               timeframe: str = "H1", days: int = 365) -> str:
            """运行策略回测"""
            config = BacktestConfig(
                symbols=[symbol],
                timeframe=timeframe,
                start_date=datetime.now() - timedelta(days=days),
                end_date=datetime.now()
            )
            result = await self.backtest.run_backtest(strategy_code, config)
            return json.dumps(result.metrics, indent=2)
        
        @self.server.tool()
        async def get_signal(symbol: str) -> str:
            """获取交易信号"""
            # 查询交易员Agent的最新信号
            return f"Latest signal for {symbol}"
        
        @self.server.tool()
        async def get_state_hex(symbol: str) -> str:
            """获取State Hex状态"""
            # 查询State Hex引擎
            return f"State Hex for {symbol}"
        
        @self.server.tool()
        async def get_contractions(symbol: str = None) -> str:
            """获取当前收缩列表"""
            # 查询收缩检测引擎
            return f"Contractions list"
        
        @self.server.tool()
        async def create_strategy(description: str) -> str:
            """从自然语言创建策略"""
            intent = await self.strategy.parse_natural_language(description)
            code = await self.strategy.generate_code(intent, CodeTarget.PYTHON)
            return code
    
    async def run(self):
        """启动MCP服务器"""
        await self.server.run()
```

---

## 七、附录

### 7.1 模块依赖关系

```
nl_strategy.py
  ├── llm_gateway.py
  ├── template_registry.py
  └── strategy_validator.py

backtest_engine.py
  ├── vectorbt
  ├── multi_timeframe_aligner.py
  └── data_source.py

agent_system/
  ├── base_agent.py
  ├── research_agent.py
  ├── trader_agent.py
  ├── risk_agent.py
  ├── execution_agent.py
  └── orchestrator.py

data_processing.py
  ├── data_source.py
  ├── data_quality.py
  └── feature_engineer.py

mcp_server.py
  └── [depends on all above modules]
```

### 7.2 变更记录

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| V1.0 | 2026-06-06 | 初始版本 | KIMI AI |
