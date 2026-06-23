"""
AI 决策引擎 - L1: LLM 快速智能层
功能：
1. 市场情绪分析
2. 交易信号解读
3. 风险提醒
4. 新闻/事件分析
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import openai
import anthropic

logger = logging.getLogger(__name__)


class Sentiment(Enum):
    """市场情绪"""
    BULLISH = "看涨"
    BEARISH = "看跌"
    NEUTRAL = "中性"
    UNCERTAIN = "不确定"


@dataclass
class AnalysisResult:
    """分析结果"""
    sentiment: Sentiment
    confidence: float  # 0-1
    recommendation: str
    risk_level: str  # LOW/MEDIUM/HIGH
    reasoning: str
    key_factors: List[str]
    timestamp: str


class LLMAnalyzer:
    """
    LLM 分析器
    
    支持多种AI服务：
    - OpenAI GPT-4
    - Anthropic Claude
    - 本地模型（未来扩展）
    """
    
    def __init__(
        self,
        provider: str = "openai",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.3
    ):
        self.provider = provider.lower()
        self.api_key = api_key or os.getenv(f"{provider.upper()}_API_KEY")
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        # 设置默认模型
        if model:
            self.model = model
        elif provider == "openai":
            self.model = "gpt-4"
        elif provider == "anthropic":
            self.model = "claude-3-opus-20240229"
        else:
            self.model = "gpt-4"
        
        # 初始化客户端
        self._init_client()
        
        logger.info(f"LLMAnalyzer初始化完成 | 提供商: {provider} | 模型: {self.model}")
    
    def _init_client(self):
        """初始化AI客户端"""
        if self.provider == "openai":
            if not self.api_key:
                raise ValueError("OpenAI API Key未设置")
            openai.api_key = self.api_key
        elif self.provider == "anthropic":
            if not self.api_key:
                raise ValueError("Anthropic API Key未设置")
            self.client = anthropic.Anthropic(api_key=self.api_key)
        else:
            raise ValueError(f"不支持的AI提供商: {self.provider}")
    
    def analyze_market(
        self,
        symbol: str,
        current_price: float,
        technical_indicators: Dict[str, float],
        market_context: Optional[str] = None
    ) -> AnalysisResult:
        """
        分析市场状况
        
        Args:
            symbol: 交易品种
            current_price: 当前价格
            technical_indicators: 技术指标字典
            market_context: 额外市场信息
        """
        prompt = self._build_analysis_prompt(
            symbol, current_price, technical_indicators, market_context
        )
        
        try:
            response = self._call_llm(prompt)
            return self._parse_analysis_response(response)
        except Exception as e:
            logger.error(f"市场分析失败: {e}")
            return AnalysisResult(
                sentiment=Sentiment.UNCERTAIN,
                confidence=0,
                recommendation="分析失败，建议观望",
                risk_level="HIGH",
                reasoning=f"AI分析出错: {str(e)}",
                key_factors=[],
                timestamp=""
            )
    
    def analyze_trade_setup(
        self,
        symbol: str,
        setup_type: str,  # 如 "BREAKOUT", "REVERSAL", "TREND_FOLLOWING"
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        risk_reward_ratio: float,
        market_conditions: Dict[str, Any]
    ) -> AnalysisResult:
        """
        分析交易设置
        
        Args:
            symbol: 交易品种
            setup_type: 交易设置类型
            entry_price: 入场价格
            stop_loss: 止损价格
            take_profit: 止盈价格
            risk_reward_ratio: 风险回报比
            market_conditions: 市场条件
        """
        prompt = self._build_trade_setup_prompt(
            symbol, setup_type, entry_price, stop_loss, 
            take_profit, risk_reward_ratio, market_conditions
        )
        
        try:
            response = self._call_llm(prompt)
            return self._parse_analysis_response(response)
        except Exception as e:
            logger.error(f"交易设置分析失败: {e}")
            return AnalysisResult(
                sentiment=Sentiment.UNCERTAIN,
                confidence=0,
                recommendation="分析失败",
                risk_level="HIGH",
                reasoning=f"AI分析出错: {str(e)}",
                key_factors=[],
                timestamp=""
            )
    
    def _build_analysis_prompt(
        self,
        symbol: str,
        current_price: float,
        indicators: Dict[str, float],
        context: Optional[str]
    ) -> str:
        """构建市场分析提示词"""
        prompt = f"""你是一位专业的量化交易分析师。请基于以下数据进行分析：

交易品种: {symbol}
当前价格: {current_price}

技术指标:
"""
        for name, value in indicators.items():
            prompt += f"- {name}: {value}\n"
        
        if context:
            prompt += f"\n市场背景:\n{context}\n"
        
        prompt += """
请提供以下格式的JSON分析结果：
{
    "sentiment": "BULLISH/BEARISH/NEUTRAL",
    "confidence": 0.0-1.0,
    "recommendation": "具体的交易建议",
    "risk_level": "LOW/MEDIUM/HIGH",
    "reasoning": "详细的分析理由",
    "key_factors": ["关键因素1", "关键因素2"]
}

注意：
1. confidence必须基于技术指标的明确程度
2. 如果指标矛盾，confidence应该较低
3. 必须考虑风险管理
"""
        return prompt
    
    def _build_trade_setup_prompt(
        self,
        symbol: str,
        setup_type: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        risk_reward_ratio: float,
        market_conditions: Dict[str, Any]
    ) -> str:
        """构建交易设置分析提示词"""
        return f"""你是一位专业的交易风险分析师。请评估以下交易设置：

交易品种: {symbol}
设置类型: {setup_type}
入场价格: {entry_price}
止损价格: {stop_loss}
止盈价格: {take_profit}
风险回报比: {risk_reward_ratio}:1

市场条件:
{json.dumps(market_conditions, indent=2, ensure_ascii=False)}

请评估这个交易设置的合理性，并提供JSON格式的分析：
{{
    "sentiment": "BULLISH/BEARISH/NEUTRAL",
    "confidence": 0.0-1.0,
    "recommendation": "具体的建议",
    "risk_level": "LOW/MEDIUM/HIGH",
    "reasoning": "详细的理由",
    "key_factors": ["因素1", "因素2"]
}}
"""
    
    def _call_llm(self, prompt: str) -> str:
        """调用LLM API"""
        if self.provider == "openai":
            return self._call_openai(prompt)
        elif self.provider == "anthropic":
            return self._call_anthropic(prompt)
        else:
            raise ValueError(f"不支持的提供商: {self.provider}")
    
    def _call_openai(self, prompt: str) -> str:
        """调用OpenAI API"""
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "你是一位专业的量化交易分析师。请始终返回有效的JSON格式。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=self.max_tokens,
            temperature=self.temperature
        )
        return response.choices[0].message.content
    
    def _call_anthropic(self, prompt: str) -> str:
        """调用Anthropic API"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system="你是一位专业的量化交易分析师。请始终返回有效的JSON格式。",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    
    def _parse_analysis_response(self, response: str) -> AnalysisResult:
        """解析AI响应"""
        try:
            # 提取JSON部分
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            
            data = json.loads(json_str.strip())
            
            return AnalysisResult(
                sentiment=Sentiment(data.get("sentiment", "UNCERTAIN")),
                confidence=float(data.get("confidence", 0)),
                recommendation=data.get("recommendation", ""),
                risk_level=data.get("risk_level", "HIGH"),
                reasoning=data.get("reasoning", ""),
                key_factors=data.get("key_factors", []),
                timestamp=""
            )
        except Exception as e:
            logger.error(f"解析AI响应失败: {e}")
            return AnalysisResult(
                sentiment=Sentiment.UNCERTAIN,
                confidence=0,
                recommendation="解析失败",
                risk_level="HIGH",
                reasoning=f"解析错误: {str(e)}",
                key_factors=[],
                timestamp=""
            )


if __name__ == "__main__":
    # 测试代码
    analyzer = LLMAnalyzer(provider="openai")
    
    indicators = {
        "RSI(14)": 65.5,
        "MACD": 0.0025,
        "EMA_20": 1.0850,
        "EMA_50": 1.0820,
        "ATR(14)": 0.0015,
        "BB_Width": 0.0030
    }
    
    result = analyzer.analyze_market("EURUSD", 1.0855, indicators)
    print(f"情绪: {result.sentiment.value}")
    print(f"信心度: {result.confidence:.2%}")
    print(f"建议: {result.recommendation}")
    print(f"风险等级: {result.risk_level}")
    print(f"理由: {result.reasoning}")
