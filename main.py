import argparse
import os

from app.utils.config import config_dict, set_config
from app.ui.ui_main import UIMain    

if __name__ == "__main__":
    # get args
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", choices=list(config_dict.keys()), default="dev")
    args = parser.parse_args() 

    # load config
    os.environ["ENV"] = args.env
    set_config(args.env)
    from app.utils.config import config

    # launch the app
    app = UIMain()
    app.launch(
        host=config.HOST, 
        port=config.PORT, 
        share=config.SHARE,
        inbrowser=True,
    )

    # `demo` is a predefined name used for hot reloading
    # It will report: AttributeError: module '__main__' has no attribute 'demo',
    # if `demo` is not defined inside __main__
    demo = app.body 