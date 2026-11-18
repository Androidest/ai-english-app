import gradio as gr

from app.ui.models.meta import Meta
from app.ui.models.lesson_gen_params import LESSON_GEN_PARAMS_ORDER
from app.ui.states.state_lessons import State_Lessons
from app.utils.types import Language, CEFRLevel, LANG_OPTIONS

ERROR_TEMPLATE = "<span style='color: #e39696; font-size: 16px;'>{msg}</span>"

class LessonGenInfoDialog:
    def __init__(self, state_lessons: State_Lessons):

        self.state_lessons = state_lessons

        with gr.Group(visible=False, elem_classes=["dialog-overlay"]) as self.panel:

            with gr.Column(elem_classes=["dialog-panel", "gen-dialog-panel"]):

                gr.Markdown("Lesson Generation Info", elem_classes=["dialog-message"], scale=0)
                self.cur_ai = gr.Textbox("", elem_classes=["cur-ai"], max_lines=1, scale=1, container=False)

                self.name = gr.Textbox (
                    "", 
                    label="Name", 
                    placeholder="Lesson name", 
                    scale=1, 
                    interactive=False, 
                    max_lines=1,
                )

                with gr.Row():
                    source_language = gr.Dropdown(
                        label="Learning language", 
                        choices=Language.__args__, 
                        value=Language.__args__[0], 
                        scale=1, 
                        interactive=False, 
                        min_width=80,
                    )

                    difficulty = gr.Dropdown(
                        label="Difficulty", 
                        choices=CEFRLevel.__args__, 
                        value=CEFRLevel.__args__[0], 
                        scale=1, 
                        interactive=False, 
                        min_width=80,
                    )

                    source_max_len = gr.Number(
                        100, 
                        label="Max sentence length", 
                        precision=0,
                        scale=1, 
                        interactive=False, 
                        min_width=80,
                    )

                    target_count = gr.Number(
                        10, 
                        label="Pages", 
                        precision=0,
                        scale=1, 
                        interactive=False, 
                        min_width=80,
                    )
                
                with gr.Row():
                    display_language_1 = gr.Dropdown(
                        label="Display language 1", 
                        choices=LANG_OPTIONS.__args__, 
                        value=LANG_OPTIONS.__args__[0], 
                        scale=1, 
                        interactive=False, 
                        min_width=80
                    )

                    display_language_2 = gr.Dropdown(
                        label="Display language 2", 
                        choices=LANG_OPTIONS.__args__, 
                        value=LANG_OPTIONS.__args__[0], 
                        scale=1, 
                        interactive=False,
                        min_width=80
                    )

                    batch_size = gr.Number(
                        5, 
                        label="Batch size", 
                        precision=0,
                        scale=1, 
                        interactive=False, 
                        min_width=80,
                    )

                    max_concurrency = gr.Number(
                        20, 
                        label="Max Concurrency", 
                        precision=0,
                        scale=1, 
                        interactive=False, 
                        min_width=80,
                    )

                topic = gr.TextArea (
                    "", 
                    label="Topic", 
                    placeholder="Your requirements for creating this lesson.", 
                    scale=1, 
                    interactive=False
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

                with gr.Row():
                    self.cancel_btn = gr.Button(
                        "Close",
                        scale=1,
                        min_width=80,
                        elem_classes=[
                            "dialog-cancel-btn",
                            "dialog-confirm-normal"
                        ],
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
            metas: dict[str, Meta], 
            cur_lesson: str, 
        ):
            meta = metas[cur_lesson]
            params = meta.gen_params.model_dump()
            return (
                gr.update(visible=True), # for `self.panel``
                meta.ai_model_name, # self.cur_ai
                meta.name,
                *[gr.update(value=params[field]) for field in LESSON_GEN_PARAMS_ORDER], # for `*self.form_components``
            )

        trigger.click(
            fn=on_click,
            inputs=[
                self.state_lessons.metas,
                self.state_lessons.cur_lesson,
            ],
            outputs=[
                self.panel,
                self.cur_ai,
                self.name,
                *self.form_components,
            ]
        )