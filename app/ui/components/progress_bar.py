import gradio as gr

HTML_TEMPLATE = """
<div class="progress-bar-track_0">
<div class="progress-bar-fill_0"
        style="width: calc(${value} * 100%) !important;"></div>
</div>
"""

CSS_TEMPLATE = """
.progress-bar-track_0 {{
    position: unset;
    width: {width};
    height: {height};
    border-radius: 25px;
    border-color: #e2e2e2;
    background-color: #f2f2f2;
    border-width: 1px;
    overflow: hidden;
}}
.progress-bar-fill_0 {{
    left: 0;
    top: 0;
    height: 100%;
    border-radius: 25px;
    transition: width 0.3s ease;
    background-color: {bar_color};
    z-index: 2;
}}
"""

class ProgressBar(gr.HTML):

    def __init__(self, 
        value: float = 0,
        width: str | int = "100%",
        height: str | int = 8,
        bar_color: str = "#a2deca",
        **kwargs
    ):
        super().__init__(
            value=value,
            html_template=HTML_TEMPLATE,
            css_template = CSS_TEMPLATE.format(
                width = width if type(width) == str else f"{width}px",
                height = height if type(height) == str else f"{height}px",
                bar_color = bar_color,
            ),
            **kwargs,
        )