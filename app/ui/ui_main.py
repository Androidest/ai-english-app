import gradio as gr
from app.ui.tab_ai import render_tab_ai, load_llm_configs
from app.ui.tab_lesson import render_tab_lesson, load_lessons

with gr.Blocks(fill_height=True) as demo: # 'demo' is a predefined name used for hot reloading
    # region UI Components
    state_lessons = gr.State(value={})
    state_cur_lesson = gr.State(value=-1)
    state_llm_configs = gr.State(value=[])
    state_cur_llm = gr.State(value=-1)

    gr.Markdown("# Zeenom English")
    
    with gr.Row():
        render_tab_lesson(state_lessons, state_cur_lesson, state_llm_configs, state_cur_llm)
        render_tab_ai(state_llm_configs, state_cur_llm)
        

    def on_load():
        llm_configs, cur_llm = load_llm_configs()
        lessons, cur_lesson = load_lessons()

        return (
            llm_configs, 
            cur_llm,
            lessons,
            cur_lesson
        )

    demo.load(on_load, outputs=[
        state_llm_configs,
        state_cur_llm,
        state_lessons,
        state_cur_lesson,
    ])