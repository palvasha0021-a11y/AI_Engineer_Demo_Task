import google.generativeai as genai
from src.llm.base_provider import BaseLLMProvider
from src.llm.retry import execute_with_retry
from src.utils.logger import logger


class GeminiProvider(BaseLLMProvider):
    """Tier 1 LLM Provider: Google Gemini Flash."""

    def __init__(self, model_name: str = "gemini-1.5-flash", api_key: str = ""):
        super().__init__(model_name, api_key)
        if self.is_available:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)

    async def extract_structured(self, prompt: str, system_prompt: str) -> str:
        if not self.is_available:
            raise ValueError("Gemini API key missing")

        full_prompt = f"{system_prompt}\n\nInput Content:\n{prompt}\n\nRespond ONLY with clean JSON. Do not include markdown codeblocks or explanation."

        async def _call():
            response = await self.model.generate_content_async(
                full_prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            return response.text.strip()

        return await execute_with_retry(_call, provider_name="GeminiFlash")
