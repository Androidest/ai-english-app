import gradio as gr
import time
from typing import Generic, TypeVar

from app.workflow._core_.ai_config import AIConfig 
from app.workflow._core_.llm_config import LLMConfig 
from app.workflow._core_.tts_config import TTSConfig
from app.workflow._core_.tts_runtime import PROVIDER_REGISTRY
from app.ui.dialogs.confirm_dialog import ConfirmDialog
from app.ui.states.state_llm import State_LLM 
from app.ui.states.state_tts import State_TTS
from app.ui.states.state_ai_base import State_AIBase

ERROR_TEMPLATE = """<span style="color:red;">Error: {error}</span>"""
T = TypeVar("T", bound=AIConfig)
       
class Tab_AI:

    def __init__(
        self, 
        state_llm: State_LLM, 
        state_tts: State_TTS,
        confirm_dialog: ConfirmDialog
    ):

        self.confirm_dialog = confirm_dialog
        self.state_managers: dict[str, State_AIBase] = {}

        with gr.Tab("AIs"):

            gr.Markdown(value="### Large Language Models:", elem_id="ai-config-type")
            self.render_config_list(
                state_manager = state_llm,
                manager_type = "llm",
            )

            gr.Row(min_height=5)

            gr.Markdown(value="### Text to Speech Models:", elem_id="ai-config-type")
            self.render_config_list(
                state_manager = state_tts,
                manager_type = "tts",
            )

    def render_config_list(
        self,
        state_manager: State_AIBase,
        manager_type: str,
    ):
        self.state_managers[manager_type] = state_manager
        s_manager_type = gr.State(manager_type)

        # list of ai config
        @gr.render(inputs=[state_manager.configs, state_manager.cur_model])
        def render_list(items: list[AIConfig], cur_model: int):

            items.sort(key=lambda i: i.id)

            # render all the llm config items
            for idx, item in enumerate(items):
                s_idx = gr.State(idx)
                is_selected = idx == cur_model

                # item card for each llm config
                card_selection_style = "ai-selected-item" if is_selected else "ai-deselected-item"
                with gr.Row(variant="panel", elem_classes=["ai-clickable-item"], elem_id=card_selection_style):

                    # invisible button to trigger click event for the entire item card
                    row_click = gr.Button("", elem_classes=["ai-slot-click-button"])
                    row_click.click(
                        self.on_click_item,
                        inputs=[s_idx, state_manager.configs, state_manager.cur_model, s_manager_type],
                        outputs=[state_manager.cur_model, state_manager.configs],
                    )

                    # radio circle to display the selected item
                    with gr.Column(scale=0, min_width=60, elem_classes="ai-col-vert-center"):
                        radio_selection_style = "ai-radio-circle selected" if is_selected else "ai-radio-circle"
                        gr.HTML(
                            value=f'<div class="{radio_selection_style}" data-row="{idx}"></div>',
                            elem_id=f"circle_{idx}"
                        )   

                    with gr.Column():
                        # renders form fields
                        with gr.Row(elem_id="ai-params"):
                            input_style = "ai-input-editing" if item.editing else ""
                            base_config_type = state_manager.model_type
                            params = item.model_dump()
                            form_fields = []

                            # convert the config type into a sub-class if needed
                            final_config_type = self.get_final_config_type(
                                config_type=base_config_type,
                                provider=params.get("model_provider", ""),
                            )

                            is_subtype = final_config_type != base_config_type

                            for field, info in final_config_type.model_fields.items():
                                if field in params:
                                    label = info.description
                                    value = params[field]
                                    options = getattr(info.annotation, "__args__", None)
                                    is_active = not info.deprecated
                                    active_style = "" if is_active else "ai-input-inactive"

                                    if options:
                                        input = gr.Dropdown(label=label, value=value, choices=options, elem_classes=active_style, elem_id=input_style, interactive=is_active)
                                    elif field == "api_key":
                                        buttons = ["copy"] if item.editing else []
                                        input = gr.Textbox(label=label, value=value, elem_classes=active_style, elem_id=input_style, interactive=is_active, type="password", lines=1, buttons=buttons)
                                    else:
                                        input = gr.Textbox(label=label, value=value, elem_classes=active_style, elem_id=input_style, interactive=is_active)
                                    form_fields.append(input)

                                    # if the config type is a subtype, the subtype should change when the model_provider changes.
                                    if is_subtype and field == "model_provider":
                                        input.change(
                                            self.on_change_model_provider,
                                            inputs=[s_idx, state_manager.configs, input],
                                            outputs=[state_manager.configs],
                                        )

                        error_com = gr.Markdown(value=ERROR_TEMPLATE.format(error=item.error), visible=item.error!="")

                    # button panel
                    with gr.Column(scale=0, min_width=60, elem_classes=["ai-col-vert-center"]):
                        if not is_selected:
                            if item.editing:
                                confirm_btn = gr.Button("✅", elem_classes="ai-confirm-editing", elem_id="ai-small-btn")
                                confirm_btn.click(
                                    self.on_confirm_edit, 
                                    inputs=[s_idx, state_manager.configs, s_manager_type, *form_fields],
                                    outputs=[state_manager.configs, error_com]
                                )

                                del_btn = gr.Button("↩", variant="secondary", elem_id="ai-small-btn")
                                del_btn.click(
                                    self.on_cancel_edit, 
                                    inputs=[s_idx, state_manager.configs], 
                                    outputs=[state_manager.configs],
                                ) 
                            else:
                                edit_btn = gr.Button("✏️", variant="secondary", elem_id="ai-small-btn")
                                edit_btn.click(
                                    self.on_click_edit, 
                                    inputs=[s_idx, state_manager.configs], 
                                    outputs=[state_manager.configs]
                                )

                                # both have delete button
                                del_btn = gr.Button("⛔", elem_id="ai-small-btn")
                                self.confirm_dialog.attach(
                                        del_btn,
                                        
                                        message=f"Are you sure you want to delete<br>\"<span>{item.alias}</span>\" ?<br>This cannot be undone!",
                                        confirm_text="Delete",
                                        cancel_text="Cancel",
                                        danger=True,

                                        confirm_fn=self.on_delete,
                                        confirm_inputs=[s_idx, state_manager.configs, s_manager_type, state_manager.cur_model],
                                        confirm_outputs=[state_manager.configs, state_manager.cur_model],
                                    )

                        else:
                            gr.Markdown('<span style="color:green; font-weight:bold;">Using</span>')


            # the last item is the add button
            add_btn = gr.Button("➕ Add", variant="secondary") 
            add_btn.click(
                self.on_add, 
                inputs=[state_manager.configs, s_manager_type], 
                outputs=[state_manager.configs],
            )

    def on_change_model_provider(
        self, 
        i: int, 
        old_items: list[AIConfig],
        selected_provider: str,
    ) -> list[AIConfig]:

        item = old_items[i]

        old_type = type(item)
        final_config_type = self.get_final_config_type(
            config_type=old_type,
            provider=selected_provider,
        )

        if old_type != final_config_type:
            new_item = final_config_type.model_validate({})
            new_item.id = item.id
            new_item.alias = item.alias
            new_item.api_key = item.api_key
            new_item.model_provider = selected_provider
            new_item.editing = True

            new_items = old_items
            new_items[i] = new_item
            return new_items

        return gr.skip()
                
    def on_click_edit(
        self, 
        i: int, 
        old_items: list[AIConfig]
    ) -> list[AIConfig]:
        
        new_items = old_items
        new_items[i] = new_items[i].model_copy()
        new_items[i].editing = True
        return new_items

    def on_confirm_edit(
        self, 
        index: int, 
        old_items: list[AIConfig],
        manager_type: str,
        *form_field_inputs,
    ) -> list[AIConfig]:

        manager = self.state_managers[manager_type]
        base_config_type = manager.model_type
        fields = [ field for field, info in base_config_type.model_fields.items() if not info.exclude ]
        params = dict(zip(fields, form_field_inputs))

        # convert the config type into a sub-class if needed
        final_config_type = self.get_final_config_type(
            config_type=manager.model_type,
            provider=params.get("model_provider", ""),
        )

        config = final_config_type.model_validate(params)

        # validate fields
        config.validate_to_error()
        if config.error != "":
            return (
                gr.skip(),
                gr.update(value=ERROR_TEMPLATE.format(error=config.error), visible=True),
            )

        # update extra fields        
        print("on_confirm_edit: id=", old_items[index].id)
        config.id = old_items[index].id
        config.editing = False
        config.error = ""

        # save the config to file with timestamp as id and filename
        manager.save_item(config)

        # update list
        new_items = old_items
        new_items[index] = config

        return (
            new_items,
            gr.update(value="", visible=False),
        )

    def on_cancel_edit(
        self, 
        i: int, 
        old_items: list[AIConfig],
    ) -> list[AIConfig]:
        
        new_items = old_items
        if new_items[i].is_new:
            # canceling a new added config without saving
            new_items.pop(i)
        else:
            new_items[i] = new_items[i].model_copy()
            new_items[i].editing = False
            new_items[i].error = ""
        return new_items

    def on_delete(
        self, 
        i: int, 
        old_items: list[AIConfig],
        manager_type: str,
        cur_model: int,
    ) -> list[AIConfig]:
        
        self.state_managers[manager_type].delete_item(old_items[i])
        new_items = old_items
        new_items.pop(i)

        if cur_model >= len(new_items):
            cur_model = -1
            self.state_managers[manager_type].save_cur_model(cur_model)

        return new_items, cur_model

    def on_add(
        self, 
        old_items: list[AIConfig],
        manager_type: str,
    ) -> list[AIConfig]:

        manager = self.state_managers[manager_type]
        item = manager.model_type.model_validate({})

        final_config_type = self.get_final_config_type(
            config_type=manager.model_type,
            provider=item.model_provider,
        )

        if manager.model_type != final_config_type:
            item = final_config_type.model_validate({})

        item.is_new = True
        item.editing = True
        item.id = str(int(time.time())) 
        print("on_add id=", item.id)

        new_items = old_items
        new_items.append(item)
        return new_items

    def on_click_item(
        self, 
        i: int, 
        old_items: list[AIConfig], 
        old_cur_model: int,
        manager_type: str,
    ) -> tuple[int, list[AIConfig]]:
        
        if old_items[i].editing:
            new_items = old_items
            new_items[i] = new_items[i].model_copy()
            new_items[i].error = "Cannot choose this LLM while editing"
            return old_cur_model, new_items

        if i == old_cur_model:
            self.state_managers[manager_type].save_cur_model(-1)
            return -1, old_items

        self.state_managers[manager_type].save_cur_model(i)
        return i, old_items

    def get_final_config_type(
        self,
        config_type: type[T],
        provider: str,
    ):
        """
        convert the config type into a sub-class if needed
        """

        final_config_type = config_type
        if issubclass(final_config_type, TTSConfig) and provider in PROVIDER_REGISTRY:
            final_config_type = PROVIDER_REGISTRY[provider].config_type

        return final_config_type