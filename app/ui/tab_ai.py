import gradio as gr
from app.utils.llm_config import LLMConfig
from app.utils.paths import PATH_LLMS
import json
import time

PATH_CUR_LLM = PATH_LLMS / "cur_llm.txt"

def load_llm_configs() -> tuple[list[dict], int]:
    configs: list[dict] = []

    if PATH_LLMS.exists():
        for file_path in PATH_LLMS.rglob(f"*.json"):
            with open(file_path, "r", encoding="utf-8") as f:
                config = LLMConfig.model_validate_json(f.read())
                config_dict = config.model_dump()
                config_dict["editing"] = False
                config_dict["error"] = ""
                config_dict["id"] = file_path.stem
                configs.append(config_dict)

        sorted(configs, key=lambda x: x["id"])

    if PATH_CUR_LLM.exists():
        with open(PATH_CUR_LLM, "r", encoding="utf-8") as f:
            cur_llm = int(f.read())
    else:
        if len(configs) > 0:
            cur_llm = 0
        else:
            cur_llm = -1

    return configs, cur_llm

def save_llm_configs(item: dict):
    if not PATH_LLMS.exists():
        PATH_LLMS.mkdir(parents=True, exist_ok=True)

    with open(f"{PATH_LLMS}/{item['id']}.json", "w", encoding="utf-8") as f:
        config = LLMConfig.model_validate(item)
        f.write(json.dumps(config.model_dump(), ensure_ascii=False, indent=2))

def save_cur_llm(cur_llm: int):
    with open(PATH_CUR_LLM, "w", encoding="utf-8") as f:
        f.write(str(cur_llm))

def on_click_edit(i, old_items):
    new_items = [i.copy() for i in old_items]
    new_items[i]["editing"] = True
    return new_items

def on_confirm_edit(i, alias_text, model_text, base_url_text, api_key_text, old_items):
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

    save_llm_configs(new_items[i])

    new_items[i]["editing"] = False
    new_items[i]["error"] = ""
    return new_items

def on_cancel_edit(i, old_items):
    new_items = old_items.copy()
    new_items[i]["editing"] = False
    new_items[i]["error"] = ""
    return new_items

def on_delete_item(i, old_items):
    path = PATH_LLMS / f"{old_items[i]['id']}.json"
    if path.exists():
        path.unlink()

    new_items = old_items.copy()
    new_items.pop(i)

    return new_items

def on_add_new_item(old_items):
    item: dict = LLMConfig(alias="", model="", base_url="", api_key="").model_dump()
    item["editing"] = True
    new_items = old_items.copy()
    new_items.append(item)
    return new_items

def on_click_item(i, items, old_cur_llm):
    if items[i]["editing"]:
        new_items = items.copy()
        new_items[i]["error"] = "Cannot choose this LLM while editing"
        return old_cur_llm, new_items

    save_cur_llm(i)
    return i, items

def render_tab_ai(state_llm_configs: gr.State, state_cur_llm: gr.State):
    with gr.Tab("AIs") as tab_ai:
        
        # list of llms
        @gr.render(inputs=[state_llm_configs, state_cur_llm])
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
                item_row_classes = ["unselected-item", "clickable-row"]
                item_btn_panel_classes = ["unselected-item", "col-vert-center"]
                if is_selected:
                    item_row_classes = ["selected-item"]
                    item_btn_panel_classes = ["selected-item-bg", "col-vert-center"]

                # item card for each llm config
                with gr.Row(variant="panel", elem_classes=item_row_classes):

                    # invisible button to trigger click event for the entire item card
                    row_click = gr.Button("", elem_classes=["row-click-button"])
                    row_click.click(
                        on_click_item,
                        inputs=[gr.State(idx), state_llm_configs,  state_cur_llm],
                        outputs=[state_cur_llm, state_llm_configs],
                    )

                    # radio circle to display the selected item
                    with gr.Column(scale=0, min_width=60, elem_classes="col-vert-center"):
                        class_name = "radio-circle selected" if is_selected else "radio-circle"
                        circle_html = gr.HTML(
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
                                    on_confirm_edit, 
                                    inputs=[gr.State(idx), alias_in, model_in, base_url_in, api_key_in, state_llm_configs],
                                    outputs=[state_llm_configs]
                                )

                                del_btn = gr.Button("↩", variant="secondary")
                                del_btn.click(
                                    on_cancel_edit, 
                                    inputs=[gr.State(idx), state_llm_configs], 
                                    outputs=[state_llm_configs],
                                ) 
                            else:
                                edit_btn = gr.Button("✏️", variant="secondary")
                                edit_btn.click(
                                    on_click_edit, 
                                    inputs=[gr.State(idx), state_llm_configs], 
                                    outputs=[state_llm_configs]
                                )

                                # both have delete button
                                del_btn = gr.Button("🗑️", variant="stop")
                                del_btn.click(
                                    on_delete_item, 
                                    inputs=[gr.State(idx), state_llm_configs], 
                                    outputs=[state_llm_configs],
                                ) 
                        else:
                            gr.Markdown('<span style="color:green; font-weight:bold;">Using</span>')


            # the last item is the add button
            add_btn = gr.Button("➕ Add", variant="secondary") 
            add_btn.click(on_add_new_item, inputs=[state_llm_configs], outputs=[state_llm_configs])

            
