import gradio as gr
import argparse
from app.utils.config import config_dict, set_config
from app.ui.ui_main import demo    
from app.utils.paths import PATH_CSS, PATH_JS
import os

if __name__ == "__main__":
    # args
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", choices=list(config_dict.keys()), default="dev")
    args = parser.parse_args() 

    os.environ["ENV"] = args.env

    set_config(args.env)
    from app.utils.config import config

    css_paths = [
        file_path
        for file_path in PATH_CSS.rglob(f"*.css")
    ]

    with open(PATH_JS, "r", encoding="utf-8") as f:
        external_js = f.read()
        # print(external_js)

    demo.launch(
        server_name=config.HOST, 
        server_port=config.PORT, 
        inbrowser=True,
        css_paths=css_paths,
        js=external_js,
        share=config.SHARE,
    )