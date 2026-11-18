import gradio as gr
import asyncio

from app.ui.state_lessons import State_Lessons, FAV_LESSON, Meta, Cache
from app.ui.state_llms import State_LLMs
from app.ui.progress_bar import ProgressBar
from app.utils.paths import PATH_LESSONS
from app.utils.types import Language, CEFRLevel, LANG_OPTIONS
from app.workflow.schemas.lesson_generation_request import LessonGenerationRequest
from app.workflow.graphs.lesson_generator import LessonGenerator

class GenLessonDialog:
    def __init__(self, state_lessons: State_Lessons, state_llms: State_LLMs):

        self.state_lessons = state_lessons

        with gr.Group(visible=False, elem_classes=["dialog-overlay"]) as self.panel:

            with gr.Column(elem_classes=["dialog-panel", "gen-dialog-panel"]):

                # dynamic display
                gr.Markdown("AI Lesson Generator", elem_classes=["dialog-message"], scale=0)

                @gr.render(inputs=[state_llms.configs, state_llms.cur_llm])
                def render_items(llm_configs: list[dict], cur_llm: int):   
                    cur_llm_name = "-- Not Selected --"
                    if cur_llm != -1 and len(llm_configs) > cur_llm:
                        cur_llm_name = llm_configs[cur_llm].alias
                    gr.Textbox(cur_llm_name, elem_classes=["cur-ai"], max_lines=1, scale=1, container=False)

                name = gr.Textbox (
                    "", 
                    label="Name", 
                    placeholder="Lesson name", 
                    scale=1, 
                    interactive=True, 
                    max_lines=1,
                )

                with gr.Row():
                    source_language = gr.Dropdown(
                        label="Learning language", 
                        choices=Language.__args__, 
                        value=Language.__args__[0], 
                        scale=1, 
                        interactive=True, 
                        min_width=80,
                    )

                    difficulty = gr.Dropdown(
                        label="Difficulty", 
                        choices=CEFRLevel.__args__, 
                        value=CEFRLevel.__args__[0], 
                        scale=1, 
                        interactive=True, 
                        min_width=80,
                    )

                    source_max_len = gr.Number(
                        100, 
                        label="Max sentence length", 
                        precision=0,
                        scale=1, 
                        interactive=True, 
                        min_width=80,
                    )

                    target_count = gr.Number(
                        10, 
                        label="Pages", 
                        precision=0,
                        scale=1, 
                        interactive=True, 
                        min_width=80,
                    )
                
                with gr.Row():
                    display_language_1 = gr.Dropdown(
                        label="Display language 1", 
                        choices=LANG_OPTIONS.__args__, 
                        value=LANG_OPTIONS.__args__[0], 
                        scale=1, 
                        interactive=True, 
                        min_width=80
                    )

                    display_language_2 = gr.Dropdown(
                        label="Display language 2", 
                        choices=LANG_OPTIONS.__args__, 
                        value=LANG_OPTIONS.__args__[0], 
                        scale=1, 
                        interactive=True,
                        min_width=80
                    )

                    batch_size = gr.Number(
                        5, 
                        label="Batch size", 
                        precision=0,
                        scale=1, 
                        interactive=True, 
                        min_width=80,
                    )

                    max_concurrency = gr.Number(
                        20, 
                        label="Max Concurrency", 
                        precision=0,
                        scale=1, 
                        interactive=True, 
                        min_width=80,
                    )

                topic = gr.TextArea (
                    "", 
                    label="Topic", 
                    placeholder="Your requirements for creating this lesson.", 
                    scale=1, 
                    interactive=True
                )

                self.form_components = [
                    source_language,
                    source_max_len,
                    topic,
                    difficulty,
                    target_count,
                    display_language_1,
                    display_language_2,
                    batch_size,
                    max_concurrency,
                ]

                msg = gr.Markdown("", scale=0, elem_classes=["tip-msg"])
                progress_bar = ProgressBar(
                    height=10,
                    visible=False,
                )

                with gr.Row():
                    self.confirm_btn = gr.Button(
                        "Generate", 
                        scale=1,
                        min_width=80,
                        elem_classes=[
                            "dialog-confirm-btn",
                            "dialog-confirm-dark"
                        ],
                    )
                    
                    self.cancel_btn = gr.Button(
                        "Cancel",
                        scale=1,
                        min_width=80,
                        elem_classes=[
                            "dialog-cancel-btn",
                            "dialog-confirm-normal"
                        ],
                    )

                    self.confirm_btn.click(
                        fn=self.on_generate,
                        inputs=[
                            state_lessons.metas, 
                            state_llms.configs, 
                            state_llms.cur_llm, 
                            name,
                            *self.form_components,
                        ],
                        outputs=[
                            state_lessons.metas,
                            progress_bar,
                            msg, 
                            self.panel,
                            self.cancel_btn,
                            self.confirm_btn,
                            state_lessons.cache,
                        ],
                        show_progress="hidden",
                    )

                    self.cancel_btn.click(
                        fn=lambda: gr.update(visible=False),
                        inputs=None,
                        outputs=[self.panel],
                    )

    def attach(
        self, 
        trigger: gr.Button,
    ):
        def on_click(cache: Cache):
            return (
                gr.update(visible=True),
                gr.update(value=cache["source_language"]),
                gr.update(value=cache["source_max_len"]),
                gr.update(value=cache["topic"]),
                gr.update(value=cache["difficulty"]),
                gr.update(value=cache["target_count"]),
                gr.update(value=cache["display_language_1"]),
                gr.update(value=cache["display_language_2"]),
                gr.update(value=cache["batch_size"]),
                gr.update(value=cache["max_concurrency"]),
            )

        trigger.click(
            fn=on_click,
            inputs=[
                self.state_lessons.cache,
            ],
            outputs=[
                self.panel,
                *self.form_components,
            ]
        )

    async def on_generate(
        self, 
        metas: dict[str, Meta], 
        llm_configs: list, #
        cur_llm: str,  #
        name: str, #

        source_language: Language, #
        source_max_len: int, #
        topic: str, #
        difficulty: CEFRLevel, #
        target_count: int, #
        display_language_1 :Language, #
        display_language_2 :Language, #
        batch_size: int = 10, 
        max_concurrency: int = 10,
    ):

        ERROR_TEMPLATE = "<span style='color: #e39696; font-size: 16px;'>{msg}</span>"

        display_languages = []
        if display_language_1 in Language.__args__:
            display_languages.append(display_language_1)

        if display_language_2 in Language.__args__:
            display_languages.append(display_language_2)

        all_langs = [source_language] + display_languages

        error = ""
        if len(all_langs) != len(set(all_langs)):
            error = ERROR_TEMPLATE.format(msg="Source language and all the display languages must be distinct.<br>No duplicates are allowed.")

        if llm_configs is None or cur_llm >= len(llm_configs) or cur_llm < 0:
            error = ERROR_TEMPLATE.format(msg="AI is required!<br>Please add and chose one from the AI tab.")
        
        elif name == "":
            error = ERROR_TEMPLATE.format(msg="Name is required!")

        elif name.lower() == FAV_LESSON.lower():
            error = ERROR_TEMPLATE.format(msg="The name 'Favourite' has already been used for special purpose.")

        elif (PATH_LESSONS / f"{name}.xlsx").exists():
            error = ERROR_TEMPLATE.format(msg=f"Lesson with the name '{name}' already exists.")

        elif source_max_len <= 0 or source_max_len == None:
            error = ERROR_TEMPLATE.format(msg="Max sentence length should be a number bigger than 0.")

        elif topic == "":
            error = ERROR_TEMPLATE.format(msg="Topic is required!")

        elif difficulty not in CEFRLevel.__args__:
            error = ERROR_TEMPLATE.format(msg="Difficulty is required!")

        elif target_count <= 0 or target_count == None:
            error = ERROR_TEMPLATE.format(msg="Pages should be a number bigger than 0.")

        elif not display_languages:
            error = ERROR_TEMPLATE.format(msg="At least one display language is required!")

        elif batch_size <= 0 or batch_size == None:
            error = ERROR_TEMPLATE.format(msg="Batch size should be a number bigger than 0.")

        elif max_concurrency <= 0 or max_concurrency == None:
            error = ERROR_TEMPLATE.format(msg="Max concurrency should be a number bigger than 0.")

        elif llm_configs is None or cur_llm >= len(llm_configs) or cur_llm < 0:
            error = ERROR_TEMPLATE.format(msg="AI is required!<br>Please add and chose one from the AI tab.")

        if error == "":
            print(f"[Lesson Generator]")
            print(f"Lesson Name: {name}")
            print(f"Source Language: {source_language}")
            print(f"Source Max Len: {source_max_len}")
            print(f"Pages: {target_count}")
            print(f"Topic: {topic}")
            print(f"Difficulty: {difficulty}")
            print(f"Display Languages: {display_languages}")
            print(f"LLM: {cur_llm}", llm_configs[cur_llm])
            print("Start generating lesson...")

            cache = self.state_lessons.save_cache(Cache(
                source_language = source_language,
                source_max_len = source_max_len,
                topic = topic,
                difficulty = difficulty,
                target_count = target_count,
                display_language_1 = display_language_1,
                display_language_2 = display_language_2,
                batch_size = batch_size,
                max_concurrency = max_concurrency,
            ))

            try:
                yield self.build_on_generate_yields(0, cache=cache)

                request = LessonGenerationRequest(
                    source_language = source_language,
                    source_max_len = source_max_len,
                    topic = topic,
                    difficulty = difficulty,
                    target_count = target_count,
                    translation_languages=display_languages,
                    batch_size = batch_size,
                    max_concurrency = max_concurrency,
                )
                
                workflow = LessonGenerator()
                iterator = workflow.astream(
                    input=request, 
                    llm_config=llm_configs[cur_llm], 
                    user_id="TODO", 
                )

                cur_processed = 0
                total = target_count * (1 + len(display_languages)) * 2 + 1 
                async for data in iterator:
                    cur_processed += data["processed_count"]
                    print(data)
                    yield self.build_on_generate_yields(progress=cur_processed / total, metas=metas)

                yield self.build_on_generate_yields(1)

                gen_data = workflow.last_state["final_items"]
                if len(gen_data) != request.target_count:
                    raise Exception("[AI Generation error]<br>The count of generated sentences does not match the page count.")
                
                sheet = self.state_lessons.build_sheet(
                    lesson_name=name,
                    data=gen_data, 
                    display_languages_order=display_languages,
                )
                self.state_lessons.save_sheet(sheet)

                new_meta = self.state_lessons.create_default_meta(name, sheet)
                new_meta["source_language"] = source_language
                new_meta["source_max_len"] = source_max_len
                new_meta["topic"] = topic
                new_meta["difficulty"] = difficulty
                new_meta["target_count"] = target_count
                new_meta["display_languages"] = display_languages
                new_meta["batch_size"] = batch_size
                new_meta["max_concurrency"] = max_concurrency
                self.state_lessons.save_meta(new_meta, override_all=True)

                metas = metas.copy()
                metas[name] = new_meta
                gr.Info(f"Lesson `{name}` has been generated successfully!")
                print(f"Lesson `{name}` has been generated successfully!")
                await asyncio.sleep(1)

            except Exception as e:
                error = ERROR_TEMPLATE.format(msg=str(e))
                # raise e

        yield self.build_on_generate_yields(progress=None, error=error, metas=metas)

    def build_on_generate_yields(
        self,
        progress: int | None,
        error: str = "",
        metas: dict[str, Meta] = None,
        cache: Cache = None,
    ) -> tuple:

        """
        Build the returning data for `on_generate`
        """

        # start generating: first iteration
        if progress == 0:
            return (
                gr.skip(), 
                gr.update(value=0, visible=True),
                "",
                gr.skip(), 
                gr.update(interactive=False),
                gr.update(value="Generating:  0%"),
                cache,
            )
        # fineshed. close the window
        elif progress == None:
            return (
                metas,
                gr.update(visible=False),
                error,
                gr.update(visible=error!=""),
                gr.update(interactive=True),
                gr.update(value="Generate"),
                gr.skip(), 
            )
        else:
            return (
                gr.skip(), 
                gr.update(value=progress),
                "", 
                gr.skip(),
                gr.skip(),
                gr.update(value=f"Generating:  {progress*100:.1f}%"),
                gr.skip(),
            )