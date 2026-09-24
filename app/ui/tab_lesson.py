import gradio as gr
from app.utils.paths import PATH_LESSONS
from app.utils.sheet import Sheet
import json

def get_lesson_meta(sheet: Sheet, progress_idx: int = 0) -> dict:
    # TODO
    return {
        "progress_idx": progress_idx, 
    }

def generate_lesson(sheet: Sheet):
    # TODO
    sheet[0, "EN"] = "hello"
    sheet[0, "CN"] = "你好"
    sheet[0, "ID"] = "halo"

def load_lessons() -> tuple:
    lessons_meta: dict = {} # meta is for fast access to some breif info of each lesson without loading all the sheets
    lessons: dict = {} # contains the full info of each lesson including handlers of sheets and meta
    cur_lesson: str = None

    if PATH_LESSONS.exists():
        # load meta info
        lessons_meta, cur_lesson = load_meta()

        has_missing_meta = False
        # load lesson excel files
        for file_path in PATH_LESSONS.rglob(f"*.xlsx"):
            lesson_name = file_path.stem
            lessons[lesson_name] = { 
                "name": lesson_name,
                "sheet": None,
                "meta": lessons_meta.get(lesson_name, None),
            }

            # Load the lesson meta and sheet only when the meta is missing.
            if lessons[lesson_name]["meta"] is None:
                sheet = Sheet(file_path)
                lessons[lesson_name]["sheet"] = sheet
                lessons[lesson_name]["meta"] = get_lesson_meta(sheet)
                has_missing_meta = True

            elif cur_lesson is not None and cur_lesson == lesson_name and lessons[lesson_name]["sheet"] is None:
                # if current lesson is the same as the lesson name, load the sheet before entering the lesson
                lessons[lesson_name]["sheet"] = Sheet(file_path) # same in on_choose_lesson

        if has_missing_meta:
            save_meta(lessons, cur_lesson)

    return lessons, cur_lesson

def save_lesson_sheet(lessons: dict, lesson_name: str):
    if not PATH_LESSONS.exists():
        PATH_LESSONS.mkdir(parents=True, exist_ok=True)

    # save lesson sheet
    sheet : Sheet = lessons[lesson_name]["sheet"]
    if sheet is None:
        raise ValueError("Sheet sheet is None")
    
    sheet.save()

def delete_lesson_sheet(lesson_name: str):
    path = PATH_LESSONS / f"{lesson_name}.xlsx"
    if path.exists():
        path.unlink()

def load_meta() -> tuple:
    cur_lesson = None
    lessons_meta = {}

    meta_path = PATH_LESSONS/"meta.json"
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
            cur_lesson = meta["cur_lesson"]
            lessons_meta = meta["lessons_meta"]

    return lessons_meta, cur_lesson

def save_meta(lessons: dict, cur_lesson: str):
    if not PATH_LESSONS.exists():
        PATH_LESSONS.mkdir(parents=True, exist_ok=True)

    # save meta
    new_meta = {
        "cur_lesson": cur_lesson,
        "lessons_meta": { lesson_name: lesson["meta"] for lesson_name, lesson in lessons.items() },
    }

    with open(PATH_LESSONS/"meta.json", "w", encoding="utf-8") as f:
        json.dump(new_meta, f, ensure_ascii=False, indent=4)

def update_meta(lessons: dict, cur_lesson: str, progress_idx: int):
    new_lessons = lessons.copy()
    new_lessons[cur_lesson]["meta"] = get_lesson_meta(new_lessons[cur_lesson]["sheet"], progress_idx)
    save_meta(new_lessons, cur_lesson)

    return new_lessons, cur_lesson

def on_delete_lesson(old_lessons: dict, cur_lesson: str):
    new_lessons = old_lessons.copy()
    del new_lessons[cur_lesson]

    # update lesson files
    delete_lesson_sheet(cur_lesson)
    save_meta(new_lessons, cur_lesson)

    return new_lessons

def on_confirm_add_lesson(old_lessons: dict, lesson_name: str):
    # generate lesson data
    sheet = Sheet(PATH_LESSONS / f"{lesson_name}.xlsx", default_data={'EN':[], 'CN':[], 'ID':[]}, dtype=str)

    generate_lesson(sheet)

    new_lessons = old_lessons.copy()
    new_lessons[lesson_name] = { 
        "name": lesson_name,
        "sheet": sheet,
        "meta": get_lesson_meta(sheet),
    }

    # update lesson files
    new_cur_lesson = lesson_name
    save_lesson_sheet(new_lessons, new_cur_lesson)
    save_meta(new_lessons, new_cur_lesson)

    return new_lessons, new_cur_lesson

def on_click_add_lesson():
    # TODO
    return

def on_choose_lesson(lesson_name: str, old_lessons: dict):
    print(f"Choose lesson: {lesson_name}")

    new_cur_lesson = lesson_name
    # check if the lesson exists
    if lesson_name not in old_lessons:
        raise ValueError(f"Lesson {lesson_name} does not exist")

    new_lessons = old_lessons
    # update lesson sheet
    if old_lessons[lesson_name].get("sheet", None) is None:
        path = PATH_LESSONS / f"{lesson_name}.xlsx"
        if not path.exists():
            raise ValueError(f"Lesson {lesson_name} does not exist")

        new_lessons = old_lessons.copy()
        new_lessons[lesson_name]["sheet"] = Sheet(path)

    save_meta(new_lessons, new_cur_lesson)
    return new_lessons, new_cur_lesson

def on_exit_lesson():
    return None # cur_lesson is None when no lesson is selected, back to the lessons list

def render_tab_lesson(state_lessons: gr.State, state_cur_lesson: gr.State, state_llm_configs: gr.State, state_cur_llm: gr.State):

    with gr.Tab("Lessons"):

        @gr.render(inputs=[state_lessons, state_cur_lesson, state_llm_configs, state_cur_llm])
        def render_items(lessons: dict, cur_lesson: str, llm_configs: list[dict], cur_llm: int):   

            if cur_lesson == None:
                with gr.Row():
                    # list of lessons
                    
                    # TODO different sorting options
                    # sort lessons by name
                    sorted_lessons = sorted(lessons.items(), key=lambda item: item[1]["name"])

                    # render all the lesson items
                    for lesson_name, lesson in sorted_lessons:
                        # data
                        meta = lesson.get("meta", None)

                        # list item: lesson entry card
                        with gr.Column(variant="panel", elem_classes=["clickable-item", "lesson-item", "lesson-item-bg"], scale=0):

                            # invisible button to trigger click event for the entire item card
                            with gr.Row(scale=0, elem_classes=["lesson-name-wrapper"]):
                                gr.Markdown(f"### {lesson_name}", elem_classes=["lesson-name"], scale=0, line_breaks=True)
                                item_btn1 = gr.Button("", elem_classes=["lesson-click-button"])
                                item_btn1.click(
                                    on_choose_lesson,
                                    inputs=[gr.State(lesson_name), state_lessons],
                                    outputs=[state_lessons, state_cur_lesson],
                                )

                            # TODO: render meta
                            gr.Markdown(f"{meta['progress_idx']}", elem_classes=["lesson-meta"], scale=0, line_breaks=True)

                            item_btn = gr.Button("", elem_classes=["lesson-click-button"])
                            item_btn.click(
                                on_choose_lesson,
                                inputs=[gr.State(lesson_name), state_lessons],
                                outputs=[state_lessons, state_cur_lesson],
                            )
                            
                    with gr.Column(variant="panel", elem_classes=["lesson-item"], scale=0):
                        # the last item is the add button
                        add_btn = gr.Button("➕", variant="secondary", elem_classes=["lesson-item"]) 
                        add_btn.click(on_click_add_lesson, inputs=[], outputs=[])

            else:
                sheet = lessons[cur_lesson]["sheet"]
                meta = lessons[cur_lesson]["meta"]
                progress_idx = meta["progress_idx"]
                

                with gr.Row():
                    exit_btn = gr.Button("↩", variant="secondary", size="sm", elem_classes=["exit-button"])
                    exit_btn.click(on_exit_lesson, inputs=[], outputs=[state_cur_lesson])

                    gr.Markdown(f"## Lesson: {cur_lesson}", elem_classes=["lesson-title"])

                with gr.Row():
                    with gr.Column(elem_classes=["lesson-content"]):
                        en = sheet[progress_idx, "EN"]
                        cn = sheet[progress_idx, "CN"]
                        id = sheet[progress_idx, "ID"]
                        
                        gr.Markdown(f"{cn}", elem_classes=["phrase"], scale=0, min_width=10)
                        gr.Markdown(f"{id}", elem_classes=["phrase"], scale=0, min_width=10)

                        words = []
                        with gr.Row(elem_classes=["lesson-content"]) as row:
                            for i, word in enumerate(en.split(' ')):
                                word = word.strip()
                                punctuation = ""

                                if not word[-1].isalpha() and word[-1] != "'":
                                    punctuation = word[-1]
                                    word = word[:-1]

                                words.append(word)
                                gr.Textbox(word, max_lines=1, scale=0, min_width=10, container=False, elem_classes=["word"], interactive=True)

                                if punctuation != "":
                                    words.append(punctuation)
                                    gr.Textbox(punctuation, max_lines=1, scale=0, min_width=10, container=False, elem_classes=["word", "punctuation"], interactive=False)

                        gr.HTML(f"", js_on_load=f'window.resizeWordTextboxes({words})')
