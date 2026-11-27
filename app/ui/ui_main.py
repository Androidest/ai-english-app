import gradio as gr

from app.ui.states.state_llm import State_LLM
from app.ui.states.state_tts import State_TTS
from app.ui.states.state_lesson import State_Lesson
from app.ui.dialogs.confirm_dialog import ConfirmDialog
from app.ui.components.tab_ai import Tab_AI
from app.ui.components.tab_lesson import Tab_Lesson
from app.ui.dialogs.gen_lesson_dialog import GenLessonDialog
from app.ui.dialogs.lesson_gen_info_dialog import LessonGenInfoDialog
from app.utils.paths import PATH_CSS, PATH_JS

class UIMain:

    def __init__(self):
        # main body
        with gr.Blocks(fill_height=True) as self.body:

            # State Manages
            self.state_llm = State_LLM()
            self.state_tts = State_TTS()
            self.state_lesson = State_Lesson()

            # popup dialogs
            confirm_dialog = ConfirmDialog()
            gen_lesson_dialog = GenLessonDialog(state_lesson=self.state_lesson, state_llm=self.state_llm)
            lesson_gen_info_dialog = LessonGenInfoDialog(state_lesson=self.state_lesson)
            
            with gr.Row():
                gr.Markdown("# Zeenom Language Learner", elem_classes=["main-title"], scale=1)

                with gr.Row(elem_classes=["cur-ai"], scale=0):
                    gr.Textbox(value="LLM", elem_id="cur-ai-title", max_lines=1, scale=0, container=False)
                    chosen_llm = gr.Textbox(elem_id="cur-ai-name", max_lines=1, scale=0, container=False)

                    self.state_llm.cur_model.change(
                        self.on_change_cur_model,
                        inputs=[self.state_llm.cur_model, self.state_llm.configs],
                        outputs=[chosen_llm]
                    )

                    self.state_llm.configs.change(
                        self.on_change_cur_model,
                        inputs=[self.state_llm.cur_model, self.state_llm.configs],
                        outputs=[chosen_llm]
                    )

                with gr.Row(elem_classes=["cur-ai"], scale=0):
                    gr.Textbox(value="TTS", elem_id="cur-ai-title", max_lines=1, scale=0, container=False)
                    chosen_tts = gr.Textbox(elem_id="cur-ai-name", max_lines=1, scale=0, container=False)
                
                    self.state_tts.cur_model.change(
                        self.on_change_cur_model,
                        inputs=[self.state_tts.cur_model, self.state_tts.configs],
                        outputs=[chosen_tts]
                    )

                    self.state_tts.configs.change(
                        self.on_change_cur_model,
                        inputs=[self.state_tts.cur_model, self.state_tts.configs],
                        outputs=[chosen_tts]
                    )

            with gr.Row():
                Tab_Lesson(
                    self.state_lesson, 
                    self.state_tts, 
                    confirm_dialog, 
                    gen_lesson_dialog, 
                    lesson_gen_info_dialog,
                )
                Tab_AI(
                    self.state_llm, 
                    self.state_tts,
                    confirm_dialog
                )
            
            self.body.load(self.on_load, outputs=self.get_load_outputs())

    def get_load_outputs(self):
        return ( 
            *self.state_lesson.outputs(),
            *self.state_llm.outputs(),
            *self.state_tts.outputs(),
        )

    def on_load(self):
        outs = (
            *self.state_lesson.load_to_outputs(),
            *self.state_llm.load_to_outputs(),
            *self.state_tts.load_to_outputs(),
        )
        print("Loading Finished")
        return outs

    def launch(
        self,
        host: str,
        port: int,
        share: bool = True,
        inbrowser: bool = True,
    ):
        """
        Start the APP
        """
        
        # load css
        css_paths = [
            file_path
            for file_path in PATH_CSS.rglob(f"*.css")
        ]

        # load js
        external_js = ""
        with open(PATH_JS, "r", encoding="utf-8") as f:
            external_js = f.read()
            # print(external_js)

        # lauch
        self.body.launch(
            server_name=host, 
            server_port=port, 
            inbrowser=inbrowser,
            css_paths=css_paths,
            js=external_js,
            share=share,
        )

    def on_change_cur_model(
        self, 
        cur_model: int, 
        configs: list
    ):
        model_name = "-- Not Selected --"
        if cur_model != -1 and len(configs) > cur_model:
            model_name = configs[cur_model].alias
        return gr.update(value=model_name)