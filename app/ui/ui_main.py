import gradio as gr
from app.ui.tab_ai import render_tab_ai, load_llm_configs
from app.ui.tab_lesson import render_tab_lesson, load_lessons

with gr.Blocks(fill_height=True) as demo: # 'demo' is a predefined name used for hot reloading
    # region UI Components
    state_lessons = gr.State(value={})
    state_cur_lesson = gr.State(value=None)
    state_llm_configs = gr.State(value=[])
    state_cur_llm = gr.State(value=-1)

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("# Zeenom English", elem_classes=["main-title"], scale=1)
        with gr.Column(scale=0, min_width=120):
            @gr.render(inputs=[state_llm_configs, state_cur_llm])
            def render_items(llm_configs: list[dict], cur_llm: int):   
                cur_llm_name = "-- Not Selected --"
                if cur_llm != -1 and len(llm_configs) > cur_llm:
                    cur_llm_name = llm_configs[cur_llm]["alias"]
                gr.Textbox(cur_llm_name, label="Current AI", scale=0)
    
    with gr.Row():
        render_tab_lesson(state_lessons, state_cur_lesson, state_llm_configs, state_cur_llm)
        render_tab_ai(state_llm_configs, state_cur_llm)
        

    def on_load():
        lessons, cur_lesson = load_lessons()
        llm_configs, cur_llm = load_llm_configs()
        print("Loading Finished")

        return (
            lessons,
            cur_lesson,
            llm_configs, 
            cur_llm,
        )

    demo.load(on_load, outputs=[
        state_lessons,
        state_cur_lesson,
        state_llm_configs,
        state_cur_llm,
    ])