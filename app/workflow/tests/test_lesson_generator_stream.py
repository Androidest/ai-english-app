# Get the LLM configs from the test env
import asyncio
from app.utils.config import set_config
set_config('test')
from app.utils.config import config
from app.utils.paths import PATH_IMAGES
from app.workflow._core_.llm_config import LLMConfig
from app.workflow.graphs.lesson_generator import LessonGenerator
from app.workflow.schemas.lesson_generation_request import LessonGenerationRequest


async def test_lesson_generator():

    llm_config = LLMConfig(
        alias="test",
        model_provider=config.TEST_MODEL_PROVIDER,
        model=config.TEST_MODEL,
        base_url=config.TEST_BASE_URL,
        api_key=config.TEST_API_KEY,
    )

    request = LessonGenerationRequest(
        source_language="English",
        source_max_len=100,
        topic="Travel and everyday situations",
        target_count=10,
        difficulty="A1",

        translation_languages=["Chinese"],

        batch_size=5,
        max_concurrency=10,
    )

    workflow = LessonGenerator()

    async for data in workflow.astream(input=request, llm_config=llm_config, user_id="xxx"):
        print(data)
    
    for item in workflow.last_state["final_items"]:
        print("---------------------------------")
        for k,v in item.items():
            assert v.strip()
            print(f"{k}: {v}")

    print("==============[logs]=================")
    for log in workflow.last_state["logs"]:
        print(log)

if __name__ == "__main__":
    asyncio.run(test_lesson_generator())
