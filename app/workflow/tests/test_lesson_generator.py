# Get the LLM configs from the test env
from app.utils.config import set_config
set_config('test')
from app.utils.config import config
from app.utils.paths import PATH_IMAGES

from app.workflow._core_.llm_config import LLMConfig
from app.workflow.graphs.lesson_generator import LessonGenerator
from app.workflow.schemas.lesson_generation_request import LessonGenerationRequest


def test_lesson_generator():

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
        target_count=5,
        difficulty="A1",

        translation_languages=["Chinese", "Indonesian"],

        batch_size=3,
        max_concurrency=10,
    )

    workflow = LessonGenerator()
    workflow.draw_graph_png(PATH_IMAGES/'lesson_generator_v2.png')

    items = workflow.invoke(
        input=request,
        llm_config=llm_config,
        user_id="xxx",
    )
    
    # for batch in items:
    #     print("---------------------------------")
    #     for sen in batch.items:
    #         print("- ", sen.val)

    assert len(items) == request.target_count

    for item in items:
        print("---------------------------------")
        for k,v in item.items():
            assert v.strip()
            print(f"{k}: {v}")

if __name__ == "__main__":
    test_lesson_generator()
