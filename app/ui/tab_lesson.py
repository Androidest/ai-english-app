import gradio as gr
from app.utils.paths import PATH_LESSONS
from app.utils.sheet import Sheet
import json

# region Lesson Management Functions
IS_FAVORITE = 0b01
IS_PASSED = 0b10

ERROR_TEMPLATE = "<span style='color: #e39696; font-size: 18px;'>{msg}</span>"
CORRECT_TEMPLATE = "<span style='color: #6ce38a; font-size: 35px;'>{msg}</span>"
PASSED_MSG = CORRECT_TEMPLATE.format(msg="🌟Well done!💯✅")

def generate_lesson(sheet_path: str):
    sheet = Sheet(sheet_path, default_data={'EN':[], 'CN':[], 'ID':[]}, dtype=str)
    sheet[0, "EN"] = "hello"
    sheet[0, "CN"] = "你好"
    sheet[0, "ID"] = "halo"
    return sheet

def save_lesson_sheet(lessons: dict, lesson_name: str):
    if not PATH_LESSONS.exists():
        PATH_LESSONS.mkdir(parents=True, exist_ok=True)

    # save lesson sheet
    sheet : Sheet = lessons[lesson_name]["sheet"]
    if sheet is None:
        raise ValueError("Sheet sheet is None")
    
    sheet.save()

def load_sheet(lesson_name: str) -> Sheet:
    path = PATH_LESSONS / f"{lesson_name}.xlsx"
    if not path.exists():
        raise ValueError(f"Lesson {lesson_name} does not exist")

    sheet = Sheet(path)
    return sheet

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
                lessons[lesson_name]["meta"] = generate_lesson_meta(load_sheet(lesson_name))
                has_missing_meta = True

            elif cur_lesson == lesson_name:
                # if current lesson is the same as the lesson name, load the sheet before entering the lesson
                lessons[lesson_name]["sheet"] = load_sheet(lesson_name)

        if has_missing_meta:
            save_meta(lessons, cur_lesson)

    return lessons, cur_lesson

def delete_lesson_sheet(lesson_name: str):
    path = PATH_LESSONS / f"{lesson_name}.xlsx"
    if path.exists():
        path.unlink()

# endregion Lesson Management Functions

# region Meta Management Functions

def generate_lesson_meta(sheet: Sheet, progress_idx: int = 0) -> dict:
    # TODO
    return {
        "progress_idx": progress_idx, 
        "phrases_flag": {},
    }

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

def delete_lesson_meta(lessons: dict, lesson_name: str, new_cur_lesson: str = None):
    del lessons[lesson_name]
    save_meta(lessons, new_cur_lesson)

def update_progress(lessons: dict, cur_lesson: str, progress_idx: int):
    lessons[cur_lesson]["meta"]["progress_idx"] = progress_idx
    save_meta(lessons, cur_lesson)

# endregion Meta Management Functions

# region UI events

def on_delete_lesson(old_lessons: dict, cur_lesson: str):
    new_lessons = { **old_lessons } # shallow copy
    delete_lesson_sheet(cur_lesson)
    delete_lesson_meta(new_lessons, cur_lesson, new_cur_lesson=None)
    return new_lessons

def on_confirm_add_lesson(old_lessons: dict, lesson_name: str):
    # generate lesson data
    sheet = generate_lesson(PATH_LESSONS / f"{lesson_name}.xlsx")

    new_lessons = { **old_lessons } # shallow copy
    new_lessons[lesson_name] = { 
        "name": lesson_name,
        "sheet": sheet,
        "meta": generate_lesson_meta(sheet, 0),
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
        new_lessons = { **old_lessons } # shallow copy
        new_lessons[lesson_name]["sheet"] = load_sheet(lesson_name)

    save_meta(new_lessons, new_cur_lesson)
    return new_lessons, new_cur_lesson

def on_exit_lesson(lessons: dict):
    cur_lesson = None
    save_meta(lessons, cur_lesson)
    return cur_lesson # cur_lesson is None when no lesson is selected, back to the lessons list

def on_click_prev(lessons: dict, cur_lesson: str, progress_idx: int):
    if progress_idx > 0:
        new_lessons = { **lessons } # shallow copy
        update_progress(lessons, cur_lesson, progress_idx - 1)
        return new_lessons

def on_click_next(lessons: dict, cur_lesson: str, progress_idx: int):
    if progress_idx < len(lessons[cur_lesson]["sheet"])-1:
        new_lessons = { **lessons } # shallow copy
        update_progress(new_lessons, cur_lesson, progress_idx + 1)
        return new_lessons

def on_click_submit(lessons: dict, cur_lesson: str, progress_idx: int, words: list[str], *inputs):
    message = ""
    incorrect_count = 0
    case_incorrect_count = 0

    for w, iw in zip(words, inputs):
        if iw == "":
            message = ERROR_TEMPLATE.format(msg="Please fill in all the blanks. ")
        elif iw != w:
            incorrect_count += 1
            if iw.lower() == w.lower():
                case_incorrect_count += 1

    if case_incorrect_count > 0:
        if case_incorrect_count == 1:
            message += ERROR_TEMPLATE.format(msg=f"{case_incorrect_count} word has case issue. ")
        else:
            message += ERROR_TEMPLATE.format(msg=f"{case_incorrect_count} words have case issue. ")

    incorrect_count = incorrect_count - case_incorrect_count
    if incorrect_count > 0:
        if incorrect_count == 1:
            message += ERROR_TEMPLATE.format(msg=f"{incorrect_count} word is incorrect.")
        else:
            message += ERROR_TEMPLATE.format(msg=f"{incorrect_count} words are incorrect.")

    if message == "":
        message = PASSED_MSG
        new_lessons = lessons.copy() # shallow copy
        meta = new_lessons[cur_lesson]["meta"]
        meta["phrases_flag"][str(progress_idx)] = meta["phrases_flag"].get(str(progress_idx), 0) | IS_PASSED
        save_meta(new_lessons, cur_lesson)
        return new_lessons, message

    return lessons, message

def on_click_favourite(lessons: dict, cur_lesson: str, progress_idx: int):
    new_lessons = lessons.copy() # shallow copy
    meta = new_lessons[cur_lesson]["meta"]
    meta["phrases_flag"][str(progress_idx)] = meta["phrases_flag"].get(str(progress_idx), 0) ^ IS_FAVORITE
    save_meta(lessons, cur_lesson)
    return new_lessons

def on_click_restart(lessons: dict, cur_lesson: str):
    new_lessons = { **lessons } # shallow copy
    meta = new_lessons[cur_lesson]["meta"]
    
    meta["phrases_flag"] = {
        idx: flag & ~IS_PASSED
        for idx, flag in meta["phrases_flag"].items() if flag != IS_PASSED
    }

    meta["progress_idx"] = 0
    save_meta(new_lessons, cur_lesson)
    return new_lessons

# endregion UI events

# region UI Components

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
                is_favourite = meta["phrases_flag"].get(str(progress_idx), 0) & IS_FAVORITE
                is_passed = meta["phrases_flag"].get(str(progress_idx), 0) & IS_PASSED
                print(meta)

                if progress_idx < 0:
                    progress_idx = 0
                elif progress_idx >= len(sheet):
                    progress_idx = len(sheet)-1

                with gr.Row(min_height=80):
                    exit_btn = gr.Button("↩", variant="secondary", size="sm", elem_classes=["exit-button"])
                    exit_btn.click(on_exit_lesson, inputs=[state_lessons], outputs=[state_cur_lesson])

                    gr.Markdown(f"## Lesson: {cur_lesson}", elem_classes=["lesson-title"])

                with gr.Row():
                    with gr.Column(elem_classes=["lesson-content"]):
                        en = sheet[progress_idx, "EN"]
                        cn = sheet[progress_idx, "CN"]
                        id = sheet[progress_idx, "ID"]
                        
                        gr.Markdown(f"{cn}", elem_classes=["phrase"], scale=0, min_width=10)
                        gr.Markdown(f"{id}", elem_classes=["phrase"], scale=0, min_width=10)

                        words = []
                        all = []
                        inputs = []
                        with gr.Row(elem_classes=["phrase-en"]) as row:
                            for i, word in enumerate(en.split(' ')):
                                word = word.strip()
                                punctuation = ""

                                if not word[-1].isalpha() and word[-1] != "'":
                                    punctuation = word[-1]
                                    word = word[:-1]

                                words.append(word)
                                all.append(word)

                                input = gr.Textbox(word if is_passed else "", max_lines=1, scale=0, min_width=10, container=False, elem_classes=["word", "text-input"], interactive=True, max_length=len(word))
                                inputs.append(input)
                                
                                if punctuation != "":
                                    all.append(punctuation)
                                    gr.Textbox(punctuation, max_lines=1, scale=0, min_width=10, container=False, elem_classes=["word", "word-punct"], interactive=False)

                            gr.HTML(f"", elem_classes=["script"], js_on_load=f'window.updateTextboxes({all})')

                with gr.Row(min_height=10, elem_classes=["tip-bar"]):
                    with gr.Column(scale=0, min_width=100):
                        gr.HTML(f"<div class='tip-bubble tip-incorrect'>incorrect</div>")
                    with gr.Column(scale=0, min_width=100):
                        gr.HTML(f"<div class='tip-bubble tip-case-issue'>case issue</div>")
                    with gr.Column(scale=0, min_width=100):
                        gr.HTML(f"<div class='tip-bubble tip-partially'>partially</div>")
                    with gr.Column(scale=0, min_width=100):
                        gr.HTML(f"<div class='tip-bubble tip-correct'>correct</div>")

                msg = gr.Markdown(PASSED_MSG if is_passed else "", scale=0, elem_classes=["tip-msg"])
                with gr.Row(min_height=10, elem_classes=["button-bar"]):
                    with gr.Column(scale=0, min_width=50):
                        btn = gr.Button("↺")
                        btn.click(on_click_restart, inputs=[state_lessons, state_cur_lesson], outputs=[state_lessons])
                    with gr.Column(scale=0, min_width=100):
                        btn = gr.Button("◀", interactive=progress_idx > 0)
                        btn.click(on_click_prev, inputs=[state_lessons, state_cur_lesson, gr.State(progress_idx)], outputs=[state_lessons])
                    with gr.Column(scale=0, min_width=120):
                        submit_btn = gr.Button("⏏ submit", elem_classes=["submit-button"])
                        submit_btn.click(on_click_submit, inputs=[state_lessons, state_cur_lesson, gr.State(progress_idx), gr.State(words)] + inputs, outputs=[state_lessons, msg])
                    with gr.Column(scale=0, min_width=100):
                        btn = gr.Button("▶", interactive=progress_idx < len(sheet)-1)
                        btn.click(on_click_next, inputs=[state_lessons, state_cur_lesson, gr.State(progress_idx)], outputs=[state_lessons])
                    with gr.Column(scale=0, min_width=50):
                        btn = gr.Button("★", elem_classes="favourite-on" if is_favourite else "favourite-off")
                        btn.click(on_click_favourite, inputs=[state_lessons, state_cur_lesson, gr.State(progress_idx)], outputs=[state_lessons])

# endregion UI Components
