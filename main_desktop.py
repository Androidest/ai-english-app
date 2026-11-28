import os
import sys
import multiprocessing
import webview

# Ensure the working directory is the directory where the exe is located, 
# so that relative paths such as .data can be persisted correctly.
if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(sys.executable))

from app.ui.ui_main import UIMain
from app.utils.paths import PATH_ICONS


def main():
    multiprocessing.freeze_support()

    app = UIMain()
    app.launch(
        url="127.0.0.1",
        port=7878,
        share=False,
        inbrowser=False,          # Don't open the browser
        prevent_thread_lock=True, # Run launch in a background thread without blocking the main thread
    )

    webview.create_window(
        "Sentence Forge", 
        url=app.body.local_url, 
        width=1280, 
        height=800,
        text_select=True,
    )

    # It will block here until the user closes the window
    webview.start(icon=str(PATH_ICONS/"icon-64.ico"))

    # === When the user closes the window, the following cleanup logic is executed ===
    try:
        # Attempt to shut down the Gradio service
        if hasattr(app, 'body') and hasattr(app.body, 'close'):
            app.body.close()
        elif hasattr(app, 'close'):
            app.close()
    except Exception:
        pass
        
    # Force-terminate the current process regardless of whether the cleanup succeeds, to prevent background residues.
    os._exit(0)

if __name__ == "__main__":
    main()