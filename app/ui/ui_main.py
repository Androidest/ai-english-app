import gradio as gr

from app.ui.state_llms import State_LLMs
from app.ui.state_lessons import State_Lessons

from app.ui.confirm_dialog import ConfirmDialog
from app.ui.tab_ai import Tab_AI
from app.ui.tab_lesson import Tab_Lesson
from app.ui.gen_lesson_dialog import GenLessonDialog

with gr.Blocks(fill_height=True) as demo: # 'demo' is a predefined name used for hot reloading
    
    state_llms = State_LLMs()
    state_lessons = State_Lessons()

    confirm_dialog = ConfirmDialog()
    gen_lesson_dialog = GenLessonDialog(state_lessons=state_lessons, state_llms=state_llms)

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("# Zeenom English", elem_classes=["main-title"], scale=1)

        with gr.Column(scale=0, min_width=200):
            @gr.render(inputs=[state_llms.configs, state_llms.cur_llm])
            def render_ai(llm_configs: list[dict], cur_llm: int):
                cur_llm_name = "-- Not Selected --"
                if cur_llm != -1 and len(llm_configs) > cur_llm:
                    cur_llm_name = llm_configs[cur_llm]["alias"]
                gr.Textbox(cur_llm_name, elem_classes=["cur-ai"], max_lines=1, scale=0, min_width=200, container=False)

    with gr.Row():
        Tab_Lesson(state_lessons, state_llms, confirm_dialog, gen_lesson_dialog)
        Tab_AI(state_llms, confirm_dialog)

    def on_load():
        outs = state_lessons.load_to_outputs()
        outs += state_llms.load_to_outputs()
        print("Loading Finished")
        return outs

    outputs = state_lessons.outputs()
    outputs += state_llms.outputs()
    demo.load(on_load, outputs=outputs)    
