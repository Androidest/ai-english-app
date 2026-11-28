from app.ui.ui_main import UIMain    

if __name__ == "__main__":
    # launch the app
    app = UIMain()
    app.launch(
        host="127.0.0.1", 
        port="7860", 
        share=False,
        inbrowser=True,
    )