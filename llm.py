"""LLM 调用封装 + RateLimiter

API Key 与 Base URL 解析委托给 config 模块，实现：
  CLI 参数 > 环境变量 > 配置文件 > 模型名推断
"""
import os, time, threading, json
from openai import OpenAI
import config
from logger import logger

__all__ = ["RateLimiter", "LLM"]


class RateLimiter:
    def __init__(self, qps: float = 2.0):
        self.qps = float(qps)
        self.min_interval = 1.0 / self.qps if self.qps > 0 else 0
        self._lock = threading.Lock()
        self._next_time = 0.0

    def wait(self):
        if self.min_interval <= 0:
            return
        with self._lock:
            now = time.time()
            if now < self._next_time:
                time.sleep(self._next_time - now)
            self._next_time = max(now, self._next_time) + self.min_interval


class LLM:
    def __init__(self, model: str = None, api_base: str = None):
        self.model = config.resolve_model(model)
        self.api_key = config.resolve_api_key()
        self.api_base = config.resolve_base_url(self.model, api_base)

        if not self.api_key:
            logger.error("API Key not set. Please configure via environment variables:", "API Key 未设置。请通过环境变量配置：")
            logger.info("  $env:MLATE_API_KEY = \"sk-xxx\"    # Windows PowerShell")
            logger.info('  export MLATE_API_KEY="sk-xxx"       # Linux/macOS')
            raise ValueError("MLATE_API_KEY not set")

        self.client = OpenAI(base_url=self.api_base, api_key=self.api_key)

    def chat_json(self, messages: list, temperature: float = 0.2, retries: int = 2) -> dict | None:
        last_err = None
        for attempt in range(retries + 1):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=temperature,
                )
                return json.loads(resp.choices[0].message.content)
            except Exception as e:
                last_err = e
                if attempt < retries:
                    time.sleep(1)
        logger.error(f"LLM 调用失败: {last_err}", f"LLM call failed: {last_err}")
        return None
