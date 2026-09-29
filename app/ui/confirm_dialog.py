from typing import Callable
from dataclasses import dataclass
import gradio as gr

@dataclass
class ConfirmDialogData:
    message: str = ""
    confirm_text: str = ""
    cancel_text: str = ""
    danger: bool = False

class ConfirmDialog:
    def __init__(self):

        with gr.Group(visible=False, elem_classes=["dialog-overlay"]) as self.panel:
            # data
            self.display_data = gr.State(ConfirmDialogData())

            # default confirm behavior, should be overridden using the attach method
            self.execute = None
            self.pending_inputs = gr.State(None)
            self.outputs = None

            # default cancel behavior: hide the panel
            self.cancel_execute = lambda: (None, gr.update(visible=False))
            self.cancel_inputs = None
            self.cancel_outputs = [self.pending_inputs, self.panel]

            with gr.Column(elem_classes=["dialog-modal"]):

                # dynamic display
                @gr.render(inputs=[self.display_data])
                def render_confirm_dialog(data: dict):
                    gr.Markdown(data.message, elem_classes=["dialog-message"], scale=0)
                    with gr.Row():
                        self.confirm_btn = gr.Button(
                            data.confirm_text, 
                            scale=1,
                            min_width=80,
                            elem_classes=[
                                "dialog-confirm-btn", 
                                "dialog-confirm-danger" if data.danger else "dialog-confirm-normal",
                            ],
                        )
                        
                        self.cancel_btn = gr.Button(
                            data.cancel_text,
                            scale=1,
                            min_width=80,
                            elem_classes=["dialog-cancel-btn"],
                        )

                        self.confirm_btn.click(
                            fn=self.execute,
                            inputs=self.pending_inputs,
                            outputs=self.outputs,
                        ).success(
                            fn=lambda: (None, gr.update(visible=False)),
                            inputs=None,
                            outputs=[self.pending_inputs, self.panel],
                        )

                        self.cancel_btn.click(
                            fn=self.cancel_execute,
                            inputs=self.cancel_inputs,
                            outputs=self.cancel_outputs,
                        )

    def attach(
            self, 
            trigger: gr.Button, 
            inputs=None,
            # display data
            message: str = "Are you sure?",
            confirm_text: str = "Confirm",
            cancel_text: str = "Cancel",
            danger: bool = True,
        ):

        """
        attach the confirm dialog to a trigger button. 
        When the target button is clicked,
        the confirm dialog will be displayed.
        So the target button shouldn't have any other click events attached.

        trigger: 
            the trigger button that will display the confirm dialog.

        inputs: 
            'inputs' are the inputs for the target event. 
            They are cached when the dialog shows up, and then they are passed to the target event when the user clicks the Confirm button.
        """
        if inputs is None:
            inputs = []

        if not isinstance(inputs, list):
            inputs = [inputs]

        def on_success():
            return ConfirmDialogData(message, confirm_text, cancel_text, danger), gr.update(visible=True)
        
        trigger.click(
            fn=lambda *args: tuple(args),
            inputs=inputs,
            outputs=self.pending_inputs, # cache the inputs
        ).success(
            fn=on_success,
            inputs=None,
            outputs=[self.display_data, self.panel],
        )

        return self

    def on_confirm(
        self,
        fn: Callable, # the target event function
        outputs=None,
    ):
        """
        register the target event for the confirm button.

        fn: 
            the target event function. 
            It receives all the cached inputs from attach() and returns the result to outputs.

        outputs: 
            the outputs for the target event. 
            They are passed to the target event when the user clicks the Confirm button.
        """

        if outputs is None:
            self.outputs = []

        if not isinstance(outputs, list):
            self.outputs = [outputs]
        else:
            self.outputs = outputs

        def execute(args):
            if args is None:
                return None

            return fn(*args)

        self.execute = execute

        return self

    def on_cancel(
        self,
        fn: Callable,
        inputs=None,
        outputs=None,
    ):
        """
        Optional: register the target event for the cancel button.
        """
        if inputs is None:
            self.cancel_inputs = []

        if not isinstance(inputs, list):
            self.cancel_inputs = [inputs]
        else:
            self.cancel_inputs = inputs

        if outputs is None:
            self.cancel_outputs = []

        if not isinstance(outputs, list):
            self.cancel_outputs = [outputs]
        else:
            self.cancel_outputs = outputs

        self.cancel_execute = fn

        return self