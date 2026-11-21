import gradio as gr

from app.ui.states.state_llm import State_LLM
from app.ui.states.state_lesson import State_Lesson

from app.ui.dialogs.confirm_dialog import ConfirmDialog
from app.ui.components.tab_ai import Tab_AI
from app.ui.components.tab_lesson import Tab_Lesson
from app.ui.dialogs.gen_lesson_dialog import GenLessonDialog
from app.ui.dialogs.lesson_gen_info_dialog import LessonGenInfoDialog

with gr.Blocks(fill_height=True) as demo: # 'demo' is a predefined name used for hot reloading
    
    state_llm = State_LLM()
    state_lesson = State_Lesson()

    confirm_dialog = ConfirmDialog()
    gen_lesson_dialog = GenLessonDialog(state_lesson=state_lesson, state_llm=state_llm)
    lesson_gen_info_dialog = LessonGenInfoDialog(state_lesson=state_lesson)

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("# Zeenom Language Learner", elem_classes=["main-title"], scale=1)

        with gr.Column(scale=0, min_width=200):
            @gr.render(inputs=[state_llm.configs, state_llm.cur_llm])
            def render_ai(llm_configs: list[dict], cur_llm: int):
                cur_llm_name = "-- Not Selected --"
                if cur_llm != -1 and len(llm_configs) > cur_llm:
                    cur_llm_name = llm_configs[cur_llm].alias
                gr.Textbox(cur_llm_name, elem_classes=["cur-ai"], max_lines=1, scale=0, min_width=200, container=False)

    with gr.Row():
        Tab_Lesson(
            state_lesson, 
            state_llm, 
            confirm_dialog, 
            gen_lesson_dialog, 
            lesson_gen_info_dialog,
        )
        Tab_AI(
            state_llm, 
            confirm_dialog
        )

    def on_load():
        outs = state_lesson.load_to_outputs()
        outs += state_llm.load_to_outputs()
        print("Loading Finished")
        return outs

    outputs = state_lesson.outputs()
    outputs += state_llm.outputs()
    demo.load(on_load, outputs=outputs)    
