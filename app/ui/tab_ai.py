import gradio as gr
from app.utils.llm_config import LLMConfig
from app.ui.confirm_dialog import ConfirmDialog
from app.ui.state_llms import State_LLMs
import time
       
class Tab_AI:
    state_llms: State_LLMs

    def __init__(self, state_llms: State_LLMs, confirm_dialog: ConfirmDialog):
        self.state_llms = state_llms

        with gr.Tab("AIs") as tab_ai:
            # list of llms
            @gr.render(inputs=[state_llms.configs, state_llms.cur_llm])
            def render_items(items: list[dict], cur_llm: int):
                # render all the llm config items
                for idx, item in enumerate(items):
    
                    # data
                    alias = item.get("alias", "")
                    model = item.get("model", "")
                    base_url = item.get("base_url", "")
                    api_key = item.get("api_key", "")
                    is_editing = item.get("editing", False)
                    error = item.get("error", "")
                    is_selected = idx == cur_llm
    
                    # css classes for item card and button panel
                    item_row_classes = ["unselected-item", "clickable-item"]
                    item_btn_panel_classes = ["unselected-item", "col-vert-center"]
                    if is_selected:
                        item_row_classes = ["selected-item"]
                        item_btn_panel_classes = ["selected-item-bg", "col-vert-center"]
    
                    # item card for each llm config
                    with gr.Row(variant="panel", elem_classes=item_row_classes):
    
                        # invisible button to trigger click event for the entire item card
                        row_click = gr.Button("", elem_classes=["row-click-button"])
                        row_click.click(
                            self.on_click_item,
                            inputs=[gr.State(idx), state_llms.configs, state_llms.cur_llm],
                            outputs=[state_llms.cur_llm, state_llms.configs],
                        )
    
                        # radio circle to display the selected item
                        with gr.Column(scale=0, min_width=60, elem_classes="col-vert-center"):
                            class_name = "radio-circle selected" if is_selected else "radio-circle"
                            gr.HTML(
                                value=f'<div class="{class_name}" data-row="{idx}"></div>',
                                elem_id=f"circle_{idx}"
                            )   
    
                        # llm config panel
                        with gr.Column(scale=20):
                            with gr.Row():
                                # editing mode
                                if is_editing:
                                    alias_in = gr.Textbox(value=alias, label="Alias", elem_classes="input-editing", interactive=True)
                                    model_in = gr.Textbox(value=model, label="Model", elem_classes="input-editing", interactive=True)
                                    base_url_in = gr.Textbox(value=base_url, label="Base URL", elem_classes="input-editing", interactive=True)
                                    api_key_in = gr.Textbox(value=api_key, label="API Key", elem_classes="input-editing", interactive=True)
                                
                                # non-edit mode
                                else: 
                                    gr.Text(value=item.get("alias", ""), label="Alias")
                                    gr.Text(value=item.get("model", ""), label="Model")
                                    gr.Text(value=item.get("base_url", ""), label="Base URL")
                                    gr.Text(value=item.get("api_key", ""), label="API Key")
    
                            if error:
                                gr.Markdown(f'<span style="color:red;">Error: {error}</span>')
    
                        # button panel
                        with gr.Column(scale=0, min_width=60, elem_classes=item_btn_panel_classes):
                            if not is_selected:
                                if is_editing:
                                    confirm_btn = gr.Button("✅", elem_classes="confirm-editing")
                                    confirm_btn.click(
                                        self.on_confirm_edit, 
                                        inputs=[gr.State(idx), alias_in, model_in, base_url_in, api_key_in, state_llms.configs],
                                        outputs=[state_llms.configs]
                                    )
    
                                    del_btn = gr.Button("↩", variant="secondary")
                                    del_btn.click(
                                        self.on_cancel_edit, 
                                        inputs=[gr.State(idx), state_llms.configs], 
                                        outputs=[state_llms.configs],
                                    ) 
                                else:
                                    edit_btn = gr.Button("✏️", variant="secondary")
                                    edit_btn.click(
                                        self.on_click_edit, 
                                        inputs=[gr.State(idx), state_llms.configs], 
                                        outputs=[state_llms.configs]
                                    )
    
                                    # both have delete button
                                    del_btn = gr.Button("⛔")
                                    confirm_dialog.attach(
                                            del_btn,
                                            
                                            message=f"Are you sure you want to delete<br>\"<span>{alias}</span>\" ?<br>This cannot be undone!",
                                            confirm_text="Delete",
                                            cancel_text="Cancel",
                                            danger=True,
    
                                            confirm_fn=self.on_delete,
                                            confirm_inputs=[gr.State(idx), state_llms.configs],
                                            confirm_outputs=[state_llms.configs],
                                        )
    
                            else:
                                gr.Markdown('<span style="color:green; font-weight:bold;">Using</span>')
    
    
                # the last item is the add button
                add_btn = gr.Button("➕ Add", variant="secondary") 
                add_btn.click(self.on_add, inputs=[state_llms.configs], outputs=[state_llms.configs])
                
    def on_click_edit(self, i, old_items):
        new_items = [i.copy() for i in old_items]
        new_items[i]["editing"] = True
        return new_items

    def on_confirm_edit(self, i, alias_text, model_text, base_url_text, api_key_text, old_items):
        # 复制旧列表，避免原地修改state
        new_items = [i.copy() for i in old_items]
        new_items[i]["alias"] = alias_text
        new_items[i]["model"] = model_text
        new_items[i]["base_url"] = base_url_text
        new_items[i]["api_key"] = api_key_text 

        if new_items[i]["alias"] == "":
                new_items[i]["error"] = "Alias is required"
                return new_items

        if new_items[i]["model"] == "":
            new_items[i]["error"] = "Model is required"
            return new_items
            
        if new_items[i]["base_url"] == "":
            new_items[i]["error"] = "Base URL is required"
            return new_items
            
        if new_items[i]["api_key"] == "":
            new_items[i]["error"] = "API Key is required"
            return new_items
            
        # save the config to file with timestamp as id and filename
        if "id" not in new_items[i] or new_items[i]["id"] == "":
            new_items[i]["id"] = str(int(time.time())) 

        self.state_llms.save_item(new_items[i])

        new_items[i]["editing"] = False
        new_items[i]["error"] = ""
        return new_items

    def on_cancel_edit(self, i, old_items):
        new_items = old_items.copy()
        new_items[i]["editing"] = False
        new_items[i]["error"] = ""
        return new_items

    def on_delete(self, i, old_items):
        self.state_llms.delete_item(old_items[i])
        new_items = old_items.copy()
        new_items.pop(i)
        return new_items

    def on_add(self, old_items):
        item: dict = LLMConfig(alias="", model="", base_url="", api_key="").model_dump()
        item["editing"] = True
        new_items = old_items.copy()
        new_items.append(item)
        return new_items

    def on_click_item(self, i, items, old_cur_llm):
        if items[i]["editing"]:
            new_items = items.copy()
            new_items[i]["error"] = "Cannot choose this LLM while editing"
            return old_cur_llm, new_items

        self.state_llms.save_cur_llm(i)
        return i, items
        
