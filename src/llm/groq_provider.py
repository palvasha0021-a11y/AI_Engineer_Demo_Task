from groq import AsyncGroq
from src.llm.base_provider import BaseLLMProvider
from src.llm.retry import execute_with_retry
from src.utils.logger import logger


class GroqProvider(BaseLLMProvider):
    """Tier 2 LLM Provider: Groq Llama."""

    def __init__(self, model_name: str = "llama3-70b-8843", api_key: str = ""):
        super().__init__(model_name, api_key)
        if self.is_available:
            self.client = AsyncGroq(api_key=self.api_key)

    async def extract_structured(self, prompt: str, system_prompt: str) -> str:
        if not self.is_available:
            raise ValueError("Groq API key missing")

        async def _call():
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            return response.choices[0].message.content.strip()

        return await execute_with_retry(_call, provider_name="GroqLlama")
