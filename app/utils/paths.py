from pathlib import Path

PATH_PROJECT_ROOT = Path(__file__).parent.parent.parent
PATH_DATA = PATH_PROJECT_ROOT/'.data'
PATH_IMAGES = PATH_PROJECT_ROOT/'images'
PATH_LESSONS = PATH_DATA/'lessons'
PATH_LLM = PATH_DATA/'llm'
PATH_TTS = PATH_DATA/'tts'
PATH_CSS = PATH_PROJECT_ROOT/'app/ui/css'
PATH_JS = PATH_PROJECT_ROOT/'app/ui/js/script.js'