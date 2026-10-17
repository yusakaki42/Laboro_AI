"""エージェントが使うLLM（触らない）。OpenAIのモデルを使う。HANDSON_MOCK=1 のときはAPIを呼ばないモックを返す。"""

import json
import os
from typing import AsyncGenerator

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types


def get_model():
    """エージェントが使うLLMを返す。OpenAIのAPIをLiteLLM経由で呼ぶ。"""
    if os.getenv("HANDSON_MOCK") == "1":
        return MockLlm(model="mock")
    import litellm
    from google.adk.models.lite_llm import LiteLlm

    litellm.suppress_debug_info = True

    kwargs = {}
    if os.getenv("HANDSON_REASONING_EFFORT"):
        kwargs["reasoning_effort"] = os.getenv("HANDSON_REASONING_EFFORT")
    return LiteLlm(
        model="openai/" + os.getenv("HANDSON_MODEL", "gpt-5.6-terra"),
        api_key=os.getenv("OPENAI_API_KEY"),
        **kwargs,
    )


def _first_param(tool) -> str | None:
    decl = tool._get_declaration()
    if decl is None:
        return None
    if decl.parameters and decl.parameters.properties:
        return next(iter(decl.parameters.properties))
    schema = getattr(decl, "parameters_json_schema", None) or {}
    return next(iter(schema.get("properties", {})), None)


class MockLlm(BaseLlm):
    """動作確認用。ツールがあれば最初のツールを質問文で1回呼び、結果をそのまま返す。"""

    @classmethod
    def supported_models(cls) -> list[str]:
        return [r"mock"]

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        parts = llm_request.contents[-1].parts or []
        results = [p.function_response for p in parts if p.function_response]
        if results:
            text = "（モック）ツールの結果: " + json.dumps(results[0].response, ensure_ascii=False)
            yield LlmResponse(content=types.Content(role="model", parts=[types.Part(text=text)]))
            return

        question = "".join(p.text or "" for p in parts)
        if llm_request.tools_dict:
            name, tool = next(iter(llm_request.tools_dict.items()))
            param = _first_param(tool)
            call = types.FunctionCall(name=name, args={param: question} if param else {})
            yield LlmResponse(content=types.Content(role="model", parts=[types.Part(function_call=call)]))
            return

        yield LlmResponse(content=types.Content(role="model", parts=[types.Part(text="こんにちは。（モック）")]))
