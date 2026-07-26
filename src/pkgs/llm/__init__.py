"""LLM 客户端封装（OpenAI 兼容）。"""
from pkgs.llm.client import FakeLLM, LLMClient

__all__ = ["LLMClient", "FakeLLM"]
