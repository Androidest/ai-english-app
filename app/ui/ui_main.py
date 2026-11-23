import gradio as gr

from app.ui.states.state_llm import State_LLM
from app.ui.states.state_tts import State_TTS
from app.ui.states.state_lesson import State_Lesson

from app.ui.dialogs.confirm_dialog import ConfirmDialog
from app.ui.components.tab_ai import Tab_AI
from app.ui.components.tab_lesson import Tab_Lesson
from app.ui.dialogs.gen_lesson_dialog import GenLessonDialog
from app.ui.dialogs.lesson_gen_info_dialog import LessonGenInfoDialog

with gr.Blocks(fill_height=True) as demo: # 'demo' is a predefined name used for hot reloading
    
    state_llm = State_LLM()
    state_tts = State_TTS()
    state_lesson = State_Lesson()

    confirm_dialog = ConfirmDialog()
    gen_lesson_dialog = GenLessonDialog(state_lesson=state_lesson, state_llm=state_llm)
    lesson_gen_info_dialog = LessonGenInfoDialog(state_lesson=state_lesson)

    with gr.Row():
        gr.Markdown("# Zeenom Language Learner", elem_classes=["main-title"], scale=1)

        with gr.Row(elem_classes=["cur-ai"], scale=0):
            gr.Textbox(value="LLM", elem_id="cur-ai-title", max_lines=1, scale=0, container=False)
            chosen_llm = gr.Textbox(elem_id="cur-ai-name", max_lines=1, scale=0, container=False)

        with gr.Row(elem_classes=["cur-ai"], scale=0):
            gr.Textbox(value="TTS", elem_id="cur-ai-title", max_lines=1, scale=0, container=False)
            chosen_tts = gr.Textbox(elem_id="cur-ai-name", max_lines=1, scale=0, container=False)

        def on_change_cur_model(cur_model: int, configs: list):
            model_name = "-- Not Selected --"
            if cur_model != -1 and len(configs) > cur_model:
                model_name = configs[cur_model].alias
            return gr.update(value=model_name)
        
        state_llm.cur_model.change(
            on_change_cur_model,
            inputs=[state_llm.cur_model, state_llm.configs],
            outputs=[chosen_llm]
        )
        
        state_llm.cur_model.change(
            on_change_cur_model,
            inputs=[state_tts.cur_model, state_tts.configs],
            outputs=[chosen_tts]
        )

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
            state_tts,
            confirm_dialog
        )

    def on_load():
        outs = state_lesson.load_to_outputs()
        outs += state_llm.load_to_outputs()
        outs += state_tts.load_to_outputs()
        print("Loading Finished")
        return outs

    outputs = state_lesson.outputs()
    outputs += state_llm.outputs()
    outputs += state_tts.outputs()
    demo.load(on_load, outputs=outputs)    
