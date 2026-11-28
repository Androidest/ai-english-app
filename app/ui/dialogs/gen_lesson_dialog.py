import gradio as gr
import asyncio

from app.ui.models.cache import Cache
from app.ui.models.meta import Meta
from app.ui.models.lesson_gen_params import LessonGenParams, LESSON_GEN_PARAMS_ORDER
from app.ui.states.state_lesson import State_Lesson, FAV_LESSON
from app.ui.states.state_llm import State_LLM
from app.workflow._core_.llm_config import LLMConfig
from app.ui.components.progress_bar import ProgressBar
from app.utils.paths import PATH_LESSONS
from app.utils.types import Language, CEFRLevel, LANG_OPTIONS

ERROR_TEMPLATE = "<span style='color: #e39696; font-size: 16px;'>{msg}</span>"

class GenLessonDialog:
    def __init__(self, state_lesson: State_Lesson, state_llm: State_LLM):

        self.state_lesson = state_lesson
        self.state_llm = state_llm

        with gr.Group(visible=False, elem_classes=["dialog-overlay"]) as self.panel:

            with gr.Column(elem_classes=["dialog-panel", "gen-dialog-panel"]):

                gr.Markdown("AI Lesson Generator", elem_classes=["dialog-message"], scale=0)

                with gr.Row(elem_classes=["cur-ai"], scale=0):
                    gr.Textbox(value="Current AI", elem_id="cur-ai-title", max_lines=1, scale=0, container=False)
                    self.cur_ai = gr.Textbox(elem_id="cur-ai-name", max_lines=1, scale=0, container=False)

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
                    interactive=True,
                    elem_id="topic"
                )

                # Order matters here: The order of components must match the field declaration order in `LessonGenParams`.
                # Must match `LESSON_GEN_PARAMS_ORDER`
                self.form_components = [
                    # order in the parent class `LessonGenerationRequest`
                    source_language,
                    source_max_len,
                    topic,
                    difficulty,
                    target_count,
                    batch_size,
                    max_concurrency,
                    # order in the LessonGenParams
                    display_language_1,
                    display_language_2,
                ]

                self.msg = gr.Textbox("", scale=0, elem_id="error-mgs", container=False, show_label=False)
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
                            state_lesson.metas, 
                            state_llm.configs, 
                            state_llm.cur_model, 
                            name,
                            *self.form_components,
                        ],
                        outputs=[
                            state_lesson.metas,
                            progress_bar,
                            self.msg, 
                            self.panel,
                            self.cancel_btn,
                            self.confirm_btn,
                            state_lesson.cache,
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
        def on_click(
            cache: Cache, 
            llm_configs: LLMConfig, 
            cur_model: int
        ):
            cur_llm_name = "-- Not Selected --"
            if cur_model != -1 and len(llm_configs) > cur_model:
                cur_llm_name = llm_configs[cur_model].alias

            params = cache.gen_params.model_dump()
            return (
                gr.update(visible=True), # for `self.panel``
                cur_llm_name, # self.cur_ai
                "", # self.msg
                *[gr.update(value=params[field]) for field in LESSON_GEN_PARAMS_ORDER], # for `*self.form_components``
            )

        trigger.click(
            fn=on_click,
            inputs=[
                self.state_lesson.cache,
                self.state_llm.configs,
                self.state_llm.cur_model,
            ],
            outputs=[
                self.panel,
                self.cur_ai,
                self.msg,
                *self.form_components,
            ]
        )

    async def on_generate(
        self, 
        metas: dict[str, Meta], 
        llm_configs: list[LLMConfig], #
        cur_model: int,  #
        name: str, #
        *form_params,
    ):
        
        error = ""
        if llm_configs is None or cur_model >= len(llm_configs) or cur_model < 0:
            error = "AI is required!\nPlease add and chose one from the AI tab."

        elif name == "":
            error = "`Name` is required!"

        elif name.lower() == FAV_LESSON.lower():
            error = "The name `Favourite` has already been used for special purpose."

        elif (PATH_LESSONS / f"{name}.xlsx").exists():
            error = f"Lesson with the name `{name}` already exists."

        # check for empty parameters
        param_dict = dict(zip(LESSON_GEN_PARAMS_ORDER, form_params))
        for k, v in param_dict.items():
            if v == None:
                error = f"`{k}` is required!"
                break

        # validate all generation parameters
        if error == "":
            # convert form_params into LessonGenParams
            gen_params = LessonGenParams(**param_dict)
            ok, errors = gen_params.validate()
            if not ok:
                error = errors[0]

        if error == "":
            print(f"[Lesson Generator]")
            print(f"Lesson Name: {name}")
            print(f"LLM: {cur_model}", llm_configs[cur_model])
            print(gen_params.model_dump_json(indent=1))
            print("Start generating lesson...")

            try:
                # Save the form into the cache and start the process
                cache = self.state_lesson.save_cache(gen_params=gen_params)
                yield self.build_on_generate_yields(0, cache=cache)
                await asyncio.sleep(0.02)

                # prepare the workflow
                from app.workflow.schemas.lesson_generation_request import LessonGenerationRequest
                from app.workflow.graphs.lesson_generator import LessonGenerator
                gen_req: LessonGenerationRequest = gen_params.to_request()
                workflow = LessonGenerator()
                iterator = workflow.astream(
                    input=gen_req, 
                    llm_config=llm_configs[cur_model], 
                    user_id="TODO", 
                )

                # start the iteration
                cur_processed = 0
                total = gen_req.target_count * (1 + len(gen_req.translation_languages)) * 2 + 1 
                async for data in iterator:
                    cur_processed += data["processed_count"]
                    print(data)
                    yield self.build_on_generate_yields(progress=cur_processed / total, metas=metas)
                yield self.build_on_generate_yields(1)

                # validate the result
                gen_data = workflow.last_state["final_items"]
                if len(gen_data) != gen_req.target_count:
                    raise Exception("[AI Generation error]\nThe count of generated sentences does not match the page count.")

                # convert the result data into sheet
                sheet = self.state_lesson.build_sheet(
                    lesson_name=name,
                    data=gen_data,
                    display_languages_order=gen_req.translation_languages,
                )
                self.state_lesson.save_sheet(sheet)

                # build the meta file of the sheet
                new_meta = self.state_lesson.create_default_meta(name, sheet, gen_params)
                new_meta = self.state_lesson.save_meta(
                    meta=new_meta,
                    ai_model_name=llm_configs[cur_model].alias,
                )
                metas = metas.copy()
                metas[name] = new_meta

                # display info
                gr.Info(f"Lesson `{name}` has been generated successfully!")
                print(f"Lesson `{name}` has been generated successfully!")
                await asyncio.sleep(1)

            except Exception as e:
                error = str(e)
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