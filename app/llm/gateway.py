
import os
import time
import uuid

from litellm import completion

from app.schemas.llm import LLMRequest, LLMResponse


class LLMGateway:
    """
    Provider-agnostic LLM gateway.

    Handles model routing, provider configuration,
    request execution and response normalization.
    """

    PROVIDER_PREFIXES = {
        "openai": "openai",
        "anthropic": "anthropic",
        "gemini": "gemini",
        "groq": "groq",
        "openrouter": "openrouter",
        "ollama": "ollama",
        "huggingface": "huggingface",
        "azure": "azure",
        "bedrock": "bedrock",
        "vertex_ai": "vertex_ai",
    }

    LOCAL_PROVIDERS = {
        "ollama",
        "lm_studio",
        "vllm",
        "local",
    }

    def generate(self, request: LLMRequest) -> LLMResponse:
        start_time = time.perf_counter()
        request_id = str(uuid.uuid4())

        provider = request.provider.lower().strip()

        model_name = self._resolve_model(
            provider=provider,
            model=request.model,
        )

        api_key = self._resolve_api_key(
            provider=provider,
            request_api_key=request.api_key,
        )

        api_base = self._resolve_api_base(
            provider=provider,
            request_api_base=request.api_base,
        )

        try:
            response = completion(
                model=model_name,
                messages=[
                    message.model_dump()
                    for message in request.messages
                ],
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                api_key=api_key,
                api_base=api_base,
                timeout=request.timeout,
            )

            latency = time.perf_counter() - start_time

            choice = response.choices[0]
            usage = response.usage

            return LLMResponse(
                provider=provider,
                model=request.model,
                content=choice.message.content or "",
                finish_reason=choice.finish_reason,
                prompt_tokens=(
                    usage.prompt_tokens if usage else None
                ),
                completion_tokens=(
                    usage.completion_tokens if usage else None
                ),
                total_tokens=(
                    usage.total_tokens if usage else None
                ),
                latency_seconds=round(latency, 4),
                request_id=request_id,
            )

        except Exception as error:
            raise RuntimeError(
                f"LLM request failed for provider '{provider}': {error}"
            ) from error

    def _resolve_model(
        self,
        provider: str,
        model: str,
    ) -> str:

        # Avoid adding a provider prefix if the caller
        # already supplied one.
        if "/" in model:
            return model

        if provider == "lm_studio":
            return f"openai/{model}"

        if provider == "vllm":
            return f"openai/{model}"

        if provider == "local":
            return f"openai/{model}"

        prefix = self.PROVIDER_PREFIXES.get(provider)

        if not prefix:
            raise ValueError(
                f"Unsupported provider: {provider}"
            )

        return f"{prefix}/{model}"

    def _resolve_api_key(
        self,
        provider: str,
        request_api_key: str | None,
    ) -> str | None:

        # Request-level key takes precedence.
        if request_api_key:
            return request_api_key

        if provider in self.LOCAL_PROVIDERS:
            return os.getenv(
                "LOCAL_LLM_API_KEY",
                "local"
            )

        environment_variables = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "groq": "GROQ_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "huggingface": "HUGGINGFACE_API_KEY",
            "azure": "AZURE_API_KEY",
            "bedrock": "AWS_ACCESS_KEY_ID",
            "vertex_ai": "GOOGLE_APPLICATION_CREDENTIALS",
        }

        variable = environment_variables.get(provider)

        if variable:
            return os.getenv(variable)

        return None

    def _resolve_api_base(
        self,
        provider: str,
        request_api_base: str | None,
    ) -> str | None:

        # Request-level endpoint takes precedence.
        if request_api_base:
            return request_api_base

        default_local_endpoints = {
            "ollama": "http://localhost:11434",
            "lm_studio": "http://localhost:1234/v1",
            "vllm": "http://localhost:8000/v1",
            "local": "http://localhost:1234/v1",
        }

        return default_local_endpoints.get(provider)


# Shared gateway instance
llm_gateway = LLMGateway()
