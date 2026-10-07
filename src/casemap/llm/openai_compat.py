"""OpenAI-compatible LLM provider (default implementation).

Works with any service exposing OpenAI's HTTP API:
  - OpenAI
  - Anthropic (via anthropic-proxy or compatible endpoint)
  - Ollama (with OpenAI compat mode)
  - vLLM, TGI, LocalAI
  - 国内模型: DeepSeek, Moonshot, Qwen, Zhipu (most expose OpenAI-compatible endpoints)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from casemap._internal.exceptions import LLMError
from casemap._internal.logger import get_logger
from casemap.llm.cache import FileCache
from casemap.llm.config import LLMConfig

_log = get_logger("llm.openai_compat")
T = TypeVar("T", bound=BaseModel)

# Strict prompt that enforces business-language output (non-technical users).
# See spec requirement #10: outputs must be readable by non-technical readers
# (product managers, QA), not by HTTP / status-code / parameter-name speakers.
BUSINESS_LANG_SYSTEM = """你是一名功能测试用例设计专家。
你的用户是非技术人员（产品经理、测试人员），他们不懂 HTTP、状态码、参数等术语。
请把每个接口的技术描述翻译成：
1. 一句业务语言的功能描述（例：「用户可以重置自己的密码」，不是「POST /reset-password」）
2. 该功能下用户能做的所有事（正向用例）
3. 用户做错/系统异常时的预期行为（逆向用例）
4. 边界情况（最大/最小/为空/特殊字符）

【绝对禁止】输出任何 HTTP 方法、状态码、参数名、字段名等技术术语。
【必须】所有标题使用「用户能做什么」「系统应该/不应该」的自然语言。"""


class OpenAICompatProvider:
    """Provider that talks OpenAI's HTTP protocol."""

    name = "openai-compat"

    def __init__(
        self,
        config: LLMConfig,
        cache: FileCache | None = None,
    ):
        self.config = config
        self._client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
            max_retries=config.max_retries,
        )
        self.cache = cache or FileCache(Path.home() / ".casemap" / "llm_cache.json")

    async def complete(self, prompt: str, *, system: str | None = None) -> str:
        cache_key = FileCache.key_for(self.config.model, system or "", prompt)
        cached = self.cache.get(cache_key)
        if isinstance(cached, str):
            _log.debug("llm cache hit (key=%s...)", cache_key[:8])
            return cached
        sys_msg = system or BUSINESS_LANG_SYSTEM
        try:
            resp = await self._client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": prompt},
                ],
                temperature=self.config.temperature,
            )
            text = resp.choices[0].message.content or ""
        except Exception as e:
            raise LLMError(f"LLM call failed: {e}") from e
        self.cache.set(cache_key, text)
        return text

    async def complete_json(
        self,
        prompt: str,
        *,
        schema: type[T],
        system: str | None = None,
    ) -> T:
        raw = await self.complete(prompt, system=system)
        # Try to parse JSON from the response; LLM may wrap in markdown fences.
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        try:
            data = json.loads(cleaned)
            return schema.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            raise LLMError(
                f"LLM returned invalid JSON for schema {schema.__name__}: {e}\n--- raw ---\n{raw}"
            ) from e
