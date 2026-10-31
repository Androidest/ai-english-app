# Get the LLM configs from the test env
from app.utils.config import set_config
set_config('test')
from app.utils.config import config

from app.workflow._commons_.llm_config import LLMConfig
from app.workflow.graphs.lesson_generator import LessonGenerator
from app.workflow.schemas.lesson_generation_request import LessonGenerationRequest


def build_llm_config() -> LLMConfig:
    return LLMConfig(
        alias="test",
        model_provider=config.TEST_MODEL_PROVIDER,
        model=config.TEST_MODEL,
        base_url=config.TEST_BASE_URL,
        api_key=config.TEST_API_KEY,
    )


def test_lesson_generator():
    request = LessonGenerationRequest(
        topic="Travel and everyday situations",
        count=10,
        difficulty="A1",
        batch_size=5,
        existing_english_sentences=[],
    )

    workflow = LessonGenerator()
    items = workflow.invoke(
        input=request,
        llm_config=build_llm_config(),
        user_id="xxx",
    )

    assert len(items) == request.count

    for item in items:
        assert item["EN"].strip()
        assert item["CN"].strip()
        assert item["ID"].strip()

    print('Items:', items)


if __name__ == "__main__":
    test_lesson_generator()
