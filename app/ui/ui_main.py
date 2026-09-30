import gradio as gr
from app.ui.tab_lesson import render_tab_lesson, load_lessons
from app.ui.confirm_dialog import ConfirmDialog
from app.ui.tab_ai import Tab_AI
from app.ui.state_llms import State_LLMs

with gr.Blocks(fill_height=True) as demo: # 'demo' is a predefined name used for hot reloading
    # region UI Components
    state_lessons = gr.State(value={})
    state_cur_lesson = gr.State(value=None)
    state_cur_sort_by = gr.State(value="")
    state_llms = State_LLMs()

    confirm_dialog = ConfirmDialog()

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("# Zeenom English", elem_classes=["main-title"], scale=1)
        with gr.Column(scale=0, min_width=200):
            @gr.render(inputs=[state_llms.configs, state_llms.cur_llm])
            def render_items(llm_configs: list[dict], cur_llm: int):   
                cur_llm_name = "-- Not Selected --"
                if cur_llm != -1 and len(llm_configs) > cur_llm:
                    cur_llm_name = llm_configs[cur_llm]["alias"]
                gr.Textbox(cur_llm_name, elem_classes=["cur-ai"], max_lines=1, scale=0, min_width=200, container=False)

    with gr.Row():
        render_tab_lesson(state_lessons, state_cur_lesson, state_cur_sort_by, state_llms.configs, state_llms.cur_llm, confirm_dialog)
        Tab_AI(state_llms, confirm_dialog)

    def on_load():
        outs = load_lessons()
        outs += state_llms.load_to_outputs()

        print("Loading Finished")
        return outs

    outputs = [state_lessons, state_cur_lesson, state_cur_sort_by] 
    outputs += state_llms.outputs()

    demo.load(on_load, outputs=outputs)    
