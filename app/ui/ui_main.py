import gradio as gr
from app.ui.tab_ai import render_tab_ai, load_llm_configs

with gr.Blocks(fill_height=True) as demo: # 'demo' is a predefined name used for hot reloading
    # region UI Components
    state_llm_configs = gr.State(value={})
    state_cur_llm = gr.State(value=-1)

    gr.Markdown("# Zeenom English")
    
    with gr.Row():
        # ========== 标签开始 ========== 
        with gr.Tab("Lessons"):
            txt_out = gr.Textbox(label="输出")

        render_tab_ai(state_llm_configs, state_cur_llm)
        

    def on_load():
        llm_configs, cur_llm = load_llm_configs()

        return (
            llm_configs, 
            cur_llm
        )

    demo.load(on_load, outputs=[
        state_llm_configs,
        state_cur_llm,
    ])