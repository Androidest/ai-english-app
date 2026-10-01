import gradio as gr
from app.ui.state_lessons import State_Lessons, FAV_LESSON
from app.ui.state_llms import State_LLMs
from app.utils.paths import PATH_LESSONS

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
                        cur_llm_name = llm_configs[cur_llm]["alias"]
                    gr.Textbox(cur_llm_name, elem_classes=["cur-ai"], max_lines=1, scale=1, container=False)

                with gr.Row():
                    name = gr.Textbox (
                        "", 
                        label="Name", 
                        placeholder="Lesson name", 
                        scale=1, 
                        interactive=True, 
                        max_lines=1
                    )

                    pages = gr.Number(
                        50, 
                        label="Pages", 
                        placeholder="Target page count", 
                        precision=0,
                        scale=1, 
                        interactive=True, 
                    )

                prompts = gr.TextArea (
                    "", 
                    label="Prompts", 
                    placeholder="Your requirements for creating this lesson.", 
                    scale=1, 
                    interactive=True
                )

                msg = gr.Markdown("", scale=0, elem_classes=["tip-msg"])
                gr.Row(min_height=10)

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
                            pages,
                            prompts,
                        ],
                        outputs=[state_lessons.metas, msg, self.panel],
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

        trigger.click(
            fn=lambda: gr.update(visible=True),
            inputs=None,
            outputs=[self.panel]
        )

    def on_generate(
            self, 
            metas: dict[str, dict], 
            llm_configs: list, 
            cur_llm: str, 
            name: str, 
            pages: int,
            prompts: str
        ) -> dict[str, dict]:

        ERROR_TEMPLATE = "<span style='color: #e39696; font-size: 16px;'>{msg}</span>"

        error = ""
        if name == "":
            error = ERROR_TEMPLATE.format(msg="Name is required!")

        elif name.lower() == FAV_LESSON.lower():
            error = ERROR_TEMPLATE.format(msg="The name 'Favourite' has already been used for special purpose.")

        elif (PATH_LESSONS / f"{name}.xlsx").exists():
            error = ERROR_TEMPLATE.format(msg=f"Lesson with the name '{name}' already exists.")

        elif pages == None or pages <= 0:
            error = ERROR_TEMPLATE.format(msg="Pages should be a number bigger than 0.")

        elif prompts == "":
            error = ERROR_TEMPLATE.format(msg="Prompts is required!")

        elif llm_configs is None or cur_llm >= len(llm_configs) or cur_llm < 0:
            error = ERROR_TEMPLATE.format(msg="AI is required!<br>Please add and chose one from the AI tab.")

        if error == "":
            print(f"[Lesson Generator]")
            print(f"Lesson Name: {name}")
            print(f"Pages: {pages}")
            print(f"Prompts: {prompts}")
            print(f"LLM: {cur_llm}", llm_configs[cur_llm])
            print("Start generating lesson...")
            
            sheet = self.state_lessons.generate_sheet(name, pages, prompts, llm_configs[cur_llm])

            metas = metas.copy()
            metas[name] = self.state_lessons.create_default_meta(name, sheet)

            self.state_lessons.save_sheet(sheet)
            self.state_lessons.save_meta(metas[name], override_all=True)

        return metas, error, gr.update(visible=error!="")