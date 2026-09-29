from typing import Callable
from dataclasses import dataclass
import gradio as gr

@dataclass
class ConfirmDialogData:
    message: str = ""
    confirm_text: str = ""
    cancel_text: str = ""
    danger: bool = False

    confirm_execute: Callable = None
    confirm_inputs: list[gr.State] = None
    confirm_outputs: list[gr.State] = None

    cancel_execute: Callable = None
    cancel_inputs: list[gr.State] = None
    cancel_outputs: list[gr.State] = None


class ConfirmDialog:
    def __init__(self):
        # data
        self.data = gr.State(ConfirmDialogData())

        with gr.Group(visible=False, elem_classes=["dialog-overlay"]) as self.panel:

            with gr.Column(elem_classes=["dialog-panel"]):

                # dynamic display
                @gr.render(inputs=[self.data])
                def render_confirm_dialog(data: ConfirmDialogData):
                    gr.Markdown(data.message, elem_classes=["dialog-message"], scale=0)
                    with gr.Row():
                        self.confirm_btn = gr.Button(
                            data.confirm_text, 
                            scale=1,
                            min_width=80,
                            elem_classes=[
                                "dialog-confirm-btn",
                                "dialog-confirm-normal"
                            ],
                        )
                        
                        self.cancel_btn = gr.Button(
                            data.cancel_text,
                            scale=1,
                            min_width=80,
                            elem_classes=[
                                "dialog-cancel-btn",
                                "dialog-confirm-dark" if data.danger else "dialog-confirm-normal"
                            ],
                        )

                        self.confirm_btn.click(
                            fn=data.confirm_execute,
                            inputs=data.confirm_inputs,
                            outputs=data.confirm_outputs,
                        ).success(
                            fn=lambda: gr.update(visible=False),
                            inputs=None,
                            outputs=[self.panel],
                        )

                        self.cancel_btn.click(
                            fn=data.cancel_execute,
                            inputs=data.cancel_inputs,
                            outputs=data.cancel_outputs,
                        ).success(
                            fn=lambda: gr.update(visible=False),
                            inputs=None,
                            outputs=[self.panel],
                        )

    def attach(
            self, 
            trigger: gr.Button, 
            # display data
            message: str = "Are you sure?",
            confirm_text: str = "Confirm",
            cancel_text: str = "Cancel",
            danger: bool = True,
            # confirm button
            confirm_fn: Callable = None,
            confirm_inputs: list[gr.State] = [],
            confirm_outputs: list[gr.State] = [],
            # cancel button
            cancel_fn: Callable = lambda: None,
            cancel_inputs: list[gr.State] = None,
            cancel_outputs: list[gr.State] = None,
        ):

        """
        attach the confirm dialog to a trigger button. 
        When the target button is clicked,
        the confirm dialog will be displayed.
        So the target button shouldn't have any other click events attached.

        trigger: 
            the trigger button that will display the confirm dialog.
        """

        trigger.click(
            fn=lambda: (
                ConfirmDialogData(
                    # display data
                    message=message, 
                    confirm_text=confirm_text,
                    cancel_text=cancel_text,
                    danger=danger,  
                    # confirm button
                    confirm_execute=confirm_fn,
                    confirm_inputs=confirm_inputs,
                    confirm_outputs=confirm_outputs,
                    # cancel button
                    cancel_execute=cancel_fn,
                    cancel_inputs=cancel_inputs,
                    cancel_outputs=cancel_outputs,
                ), 
                gr.update(visible=True)
            ),
            inputs=None,
            outputs=[
                self.data, 
                self.panel
            ]
        )