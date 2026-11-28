from pathlib import Path
from platformdirs import user_data_dir

# Windows Defaults: C:\Users\<UserName>\AppData\Local\SentenceForge\SentenceForge
PATH_DATA = Path(user_data_dir("SentenceForge", appauthor=False))
PATH_DATA.mkdir(parents=True, exist_ok=True) 

# data sub-paths
PATH_LESSONS = PATH_DATA / "lessons"
PATH_LLM     = PATH_DATA / "llm"
PATH_TTS     = PATH_DATA / "tts"
PATH_AUDIO   = PATH_DATA / "audio"

# project resource paths
PATH_PROJECT_ROOT = Path(__file__).parent.parent.parent
PATH_CSS = PATH_PROJECT_ROOT / "app/ui/css"
PATH_JS  = PATH_PROJECT_ROOT / "app/ui/js/script.js"
PATH_IMAGE   = PATH_PROJECT_ROOT / "images"
PATH_ICONS   = PATH_IMAGE / "icons"
