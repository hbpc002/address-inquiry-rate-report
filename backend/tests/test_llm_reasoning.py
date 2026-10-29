"""验证 OpenAI 兼容接口的 reasoning_content 不会被 ChatOpenAI 丢弃。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import AIMessage, AIMessageChunk

from app.core.llm import _extract_reasoning, _reasoning_chat_openai_class


def _model():
    return _reasoning_chat_openai_class()(
        model="deepseek-reasoner", api_key="test", base_url="https://example.com/v1"
    )


def test_extract_reasoning_supports_string_and_blocks():
    assert _extract_reasoning({"reasoning_content": "先看考勤"}) == "先看考勤"
    assert _extract_reasoning({"reasoning": [{"text": "先"}, {"text": "后"}]}) == "先后"
    assert _extract_reasoning({"content": "普通正文"}) == ""


def test_stream_chunk_keeps_reasoning_content():
    gen = _model()._convert_chunk_to_generation_chunk(
        {"choices": [{"delta": {"content": "", "reasoning_content": "先分析"}}]},
        AIMessageChunk,
        None,
    )
    assert isinstance(gen.message, AIMessageChunk)
    assert gen.message.additional_kwargs["reasoning_content"] == "先分析"


def test_final_response_keeps_reasoning_content():
    result = _model()._create_chat_result({
        "choices": [{
            "message": {
                "role": "assistant",
                "content": "答案",
                "reasoning_content": "先核对工时",
            },
            "finish_reason": "stop",
        }]
    })
    message = result.generations[0].message
    assert isinstance(message, AIMessage)
    assert message.content == "答案"
    assert message.additional_kwargs["reasoning_content"] == "先核对工时"
