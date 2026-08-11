import httpx
from src.llm.base_provider import BaseLLMProvider
from src.llm.retry import execute_with_retry
from src.utils.logger import logger


class DeepSeekProvider(BaseLLMProvider):
    """Tier 3 LLM Provider: DeepSeek."""

    def __init__(self, model_name: str = "deepseek-chat", api_key: str = ""):
        super().__init__(model_name, api_key)

    async def extract_structured(self, prompt: str, system_prompt: str) -> str:
        if not self.is_available:
            raise ValueError("DeepSeek API key missing")

        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }

        async def _call():
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()

        return await execute_with_retry(_call, provider_name="DeepSeek")
