import gradio as gr
from app.workflow._core_.llm_config import LLMConfig
from app.ui.dialogs.confirm_dialog import ConfirmDialog
from app.ui.states.state_llm import State_LLM, PATH_LLM
from app.utils.types import ProviderType
import time
       
class Tab_AI:
    state_llm: State_LLM

    def __init__(
        self, 
        state_llm: State_LLM, 
        confirm_dialog: ConfirmDialog
    ):
        self.state_llm = state_llm

        with gr.Tab("AIs") as tab_ai:
            # list of llms
            @gr.render(inputs=[state_llm.configs, state_llm.cur_llm])
            def render_list(items: list[LLMConfig], cur_llm: int):
                # render all the llm config items
                for idx, item in enumerate(items):
    
                    # data
                    provider = item.model_provider
                    alias = item.alias
                    model = item.model
                    base_url = item.base_url
                    api_key = item.api_key
                    is_editing = item.editing
                    error = item.error
                    is_selected = idx == cur_llm
    
                    # css classes for item card and button panel
                    item_row_classes = ["ai-deselected-item", "ai-clickable-item"]
                    item_btn_panel_classes = ["ai-deselected-item", "ai-col-vert-center"]
                    if is_selected:
                        item_row_classes = ["ai-selected-item"]
                        item_btn_panel_classes = ["ai-selected-item-bg", "ai-col-vert-center"]
    
                    # item card for each llm config
                    with gr.Row(variant="panel", elem_classes=item_row_classes):
    
                        # invisible button to trigger click event for the entire item card
                        row_click = gr.Button("", elem_classes=["ai-slot-click-button"])
                        row_click.click(
                            self.on_click_item,
                            inputs=[gr.State(idx), state_llm.configs, state_llm.cur_llm],
                            outputs=[state_llm.cur_llm, state_llm.configs],
                        )
    
                        # radio circle to display the selected item
                        with gr.Column(scale=0, min_width=60, elem_classes="ai-col-vert-center"):
                            class_name = "ai-radio-circle selected" if is_selected else "ai-radio-circle"
                            gr.HTML(
                                value=f'<div class="{class_name}" data-row="{idx}"></div>',
                                elem_id=f"circle_{idx}"
                            )   
    
                        # llm config panel
                        with gr.Column(scale=20):
                            with gr.Row():
                                # editing mode
                                if is_editing:
                                    alias_in = gr.Textbox(label="Alias", value=alias, elem_classes="ai-input-editing", interactive=True)
                                    provider_in = gr.Dropdown(label="Provider", value=provider, choices=ProviderType.__args__, elem_classes=["ai-input-editing"], interactive=True)
                                    model_in = gr.Textbox(label="Model", value=model, elem_classes="ai-input-editing", interactive=True)
                                    base_url_in = gr.Textbox(label="Base URL", value=base_url, elem_classes="ai-input-editing", interactive=True)
                                    api_key_in = gr.Textbox(label="API Key", value=api_key, elem_classes="ai-input-editing", interactive=True)
                                
                                # non-edit mode
                                else: 
                                    gr.Text(label="Alias", value=alias)
                                    gr.Dropdown(label="Provider", value=provider, choices=ProviderType.__args__, interactive=False)
                                    gr.Text(label="Model", value=model)
                                    gr.Text(label="Base URL", value=base_url)
                                    gr.Text(label="API Key", value=api_key)
    
                            if error:
                                gr.Markdown(f'<span style="color:red;">Error: {error}</span>')
    
                        # button panel
                        with gr.Column(scale=0, min_width=60, elem_classes=item_btn_panel_classes):
                            if not is_selected:
                                if is_editing:
                                    confirm_btn = gr.Button("✅", elem_classes="ai-confirm-editing", elem_id="ai-small-btn")
                                    confirm_btn.click(
                                        self.on_confirm_edit, 
                                        inputs=[gr.State(idx), provider_in, alias_in, model_in, base_url_in, api_key_in, state_llm.configs],
                                        outputs=[state_llm.configs]
                                    )
    
                                    del_btn = gr.Button("↩", variant="secondary", elem_id="ai-small-btn")
                                    del_btn.click(
                                        self.on_cancel_edit, 
                                        inputs=[gr.State(idx), state_llm.configs], 
                                        outputs=[state_llm.configs],
                                    ) 
                                else:
                                    edit_btn = gr.Button("✏️", variant="secondary", elem_id="ai-small-btn")
                                    edit_btn.click(
                                        self.on_click_edit, 
                                        inputs=[gr.State(idx), state_llm.configs], 
                                        outputs=[state_llm.configs]
                                    )
    
                                    # both have delete button
                                    del_btn = gr.Button("⛔", elem_id="ai-small-btn")
                                    confirm_dialog.attach(
                                            del_btn,
                                            
                                            message=f"Are you sure you want to delete<br>\"<span>{alias}</span>\" ?<br>This cannot be undone!",
                                            confirm_text="Delete",
                                            cancel_text="Cancel",
                                            danger=True,
    
                                            confirm_fn=self.on_delete,
                                            confirm_inputs=[gr.State(idx), state_llm.configs],
                                            confirm_outputs=[state_llm.configs],
                                        )
    
                            else:
                                gr.Markdown('<span style="color:green; font-weight:bold;">Using</span>')
    
    
                # the last item is the add button
                add_btn = gr.Button("➕ Add", variant="secondary") 
                add_btn.click(self.on_add, inputs=[state_llm.configs], outputs=[state_llm.configs])
                
    def on_click_edit(
        self, 
        i: int, 
        old_items: list[LLMConfig]
    ) -> list[LLMConfig]:
        
        new_items = [i.model_copy() for i in old_items]
        new_items[i].editing = True
        return new_items

    def on_confirm_edit(
        self, 
        i: int, 
        provider_dd: str, 
        alias_text: str, 
        model_text: str, 
        base_url_text: str, 
        api_key_text: str, 
        old_items: list[LLMConfig]
    ) -> list[LLMConfig]:
        
        new_items = [i.model_copy() for i in old_items]
        new_items[i].model_provider = provider_dd
        new_items[i].alias = alias_text
        new_items[i].model = model_text
        new_items[i].base_url = base_url_text
        new_items[i].api_key = api_key_text 

        if new_items[i].alias == "":
                new_items[i].error = "Alias is required"
                return new_items

        if new_items[i].model == "":
            new_items[i].error = "Model is required"
            return new_items
            
        if new_items[i].base_url == "":
            new_items[i].error = "Base URL is required"
            return new_items
            
        if new_items[i].api_key == "":
            new_items[i].error = "API Key is required"
            return new_items
            
        # save the config to file with timestamp as id and filename
        if new_items[i].id == "":
            new_items[i].id = str(int(time.time())) 

        self.state_llm.save_item(new_items[i])

        new_items[i].editing = False
        new_items[i].error = ""
        return new_items

    def on_cancel_edit(
        self, 
        i: int, 
        old_items: list[LLMConfig],
    ) -> list[LLMConfig]:
        
        new_items = [i.model_copy() for i in old_items]
        if new_items[i].is_new:
            # canceling a new added config without saving
            new_items.pop(i)
        else:
            new_items[i].editing = False
            new_items[i].error = ""
        return new_items

    def on_delete(
        self, 
        i: int, 
        old_items: list[LLMConfig],
    ) -> list[LLMConfig]:
        
        self.state_llm.delete_item(old_items[i])
        new_items = [i.model_copy() for i in old_items]
        new_items.pop(i)
        return new_items

    def on_add(
        self, 
        old_items: list[LLMConfig],
    ) -> list[LLMConfig]:
        
        item = LLMConfig(
            model_provider=ProviderType.__args__[0], 
            alias="", 
            model="", 
            base_url="", 
            api_key="",
            editing=True,
            is_new=True,
        )
        new_items = [i.model_copy() for i in old_items]
        new_items.append(item)
        return new_items

    def on_click_item(
        self, 
        i: int, 
        items: list[LLMConfig], 
        old_cur_llm: int
    ) -> tuple[int, list[LLMConfig]]:
        
        if items[i].editing:
            new_items = [i.model_copy() for i in items]
            new_items[i].error = "Cannot choose this LLM while editing"
            return old_cur_llm, new_items

        self.state_llm.save_cur_llm(i)
        return i, items
        
