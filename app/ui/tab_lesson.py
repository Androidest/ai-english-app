import gradio as gr
from app.utils.paths import PATH_LESSONS
from app.utils.sheet import Sheet
import json

IS_FAVORITE = 0b01
IS_PASSED = 0b10

ERROR_TEMPLATE = "<span style='color: #e39696; font-size: 18px;'>{msg}</span>"
CORRECT_TEMPLATE = "<span style='color: #6ce38a; font-size: 35px;'>{msg}</span>"
PASSED_MSG = CORRECT_TEMPLATE.format(msg="🌟Well done!💯✅")

SORT_LATEST = "latest"
SORT_OLDEST = "oldest"
SORT_ALPHA_A_Z = "A → Z"
SORT_ALPHA_Z_A = "Z → A"

# region Init

def load_lessons() -> tuple:
    lessons: dict = {} # lessons meta
    if PATH_LESSONS.exists():
        for file_path in PATH_LESSONS.rglob(f"*.xlsx"):
            lesson_name = file_path.stem
            lessons[lesson_name] = load_meta(lesson_name)

    cache = load_cache()
    cur_lesson = cache["cur_lesson"]
    cur_sort_by = cache["cur_sort_by"]

    return lessons, cur_lesson, cur_sort_by

# endregion Init

# region Cache Management

def create_default_cache() -> dict:
    return {
        "cur_lesson": "",
        "cur_sort_by": SORT_LATEST,
    }

def load_cache() -> dict:
    cache_path = PATH_LESSONS / "cache.json"
    if cache_path.exists():
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        cache = create_default_cache()
        save_cache(cache, override_all=True)
        return cache
    
def save_cache(cache: dict, override_all: bool = False):
    if not PATH_LESSONS.exists():
        PATH_LESSONS.mkdir(parents=True, exist_ok=True)
    
    cache_path = PATH_LESSONS / "cache.json"

    # Update existing cache
    if cache_path.exists() and not override_all:
        with open(cache_path, "r", encoding="utf-8") as f:
            old_cache = json.load(f)
            cache = { **old_cache, **cache }

    # Save cache to file
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=4)

    return cache

# endregion Cache Management

# region sheet Management Functions

def generate_sheet(sheet_path: str):
    # TODO
    sheet = Sheet(sheet_path, default_data={'EN':[], 'CN':[], 'ID':[]}, dtype=str)
    sheet[0, "EN"] = "hello"
    sheet[0, "CN"] = "你好"
    sheet[0, "ID"] = "halo"
    return sheet

def save_sheet(sheet: Sheet):
    if not PATH_LESSONS.exists():
        PATH_LESSONS.mkdir(parents=True, exist_ok=True)

    sheet.save()

def load_sheet(lesson_name: str) -> Sheet:
    path = PATH_LESSONS / f"{lesson_name}.xlsx"
    if not path.exists():
        raise ValueError(f"Lesson {lesson_name} does not exist")

    sheet = Sheet(path)
    return sheet

def delete_sheet(lesson_name: str):
    path = PATH_LESSONS / f"{lesson_name}.xlsx"
    if path.exists():
        path.unlink()

# endregion Lesson Management Functions

# region Meta Management Functions

def create_default_meta(lesson_name: str, sheet: Sheet) -> dict:
    meta = {
        "name": lesson_name,
        "time_created": sheet.time_created,
        "progress_idx": 0, 
        "phrases_flag": {},
    }
    meta = make_brief_meta(meta, sheet)
    return meta

def save_meta(meta: dict, override_all: bool = False):
    if not PATH_LESSONS.exists():
        PATH_LESSONS.mkdir(parents=True, exist_ok=True)

    if not (PATH_LESSONS / f"{meta['name']}.xlsx").exists():
        raise ValueError(f"Lesson {meta['name']} excel file does not exist")

    # Update existing meta
    meta_path = PATH_LESSONS / f"{meta['name']}.json"
    if meta_path.exists() and not override_all:
        with open(meta_path, "r", encoding="utf-8") as f:
            old_meta = json.load(f)
            meta = { **old_meta, **meta }

    # Save meta to file
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=4)

    return meta

def load_meta(lesson_name) -> dict:
    meta_path = PATH_LESSONS / f"{lesson_name}.json"
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        sheet = load_sheet(lesson_name)
        meta = create_default_meta(lesson_name, sheet)
        save_meta(meta, override_all=True)
        return meta

def delete_meta(lesson_name: str):
    path = PATH_LESSONS / f"{lesson_name}.json"
    if path.exists():
        path.unlink()

def make_brief_meta(meta: dict, sheet: Sheet) -> dict:
    meta["total"] = len(sheet)

    correct_count = 0
    for idx in range(0, meta["total"]):
        if is_phrase_passed(meta, idx):
            correct_count += 1
    meta["correct_count"] = correct_count

    return meta

def update_progress(meta: dict, idx: int):
    if idx < 0:
        idx = 0
    elif idx >= meta["total"]:
        idx = meta["total"] - 1
    meta["progress_idx"] = idx
    return meta

def is_phrase_passed(meta: dict, idx: int) -> bool:
    return meta["phrases_flag"].get(str(idx), 0) & IS_PASSED == IS_PASSED

def is_phrase_favourite(meta: dict, idx: int) -> bool:
    return meta["phrases_flag"].get(str(idx), 0) & IS_FAVORITE == IS_FAVORITE

def toggle_phrase_favorite(meta: dict, idx: int):
    meta["phrases_flag"][str(idx)] = meta["phrases_flag"].get(str(idx), 0) ^ IS_FAVORITE
    return meta

def set_pass_phrase(meta: dict, idx: int, is_correct: bool):
    if is_correct:
        meta["phrases_flag"][str(idx)] = meta["phrases_flag"].get(str(idx), 0) | IS_PASSED
    else:
        meta["phrases_flag"][str(idx)] = meta["phrases_flag"].get(str(idx), 0) & ~IS_PASSED
    return meta

def sort_lessons(lessons: dict, sort_by: str) -> list[(str, dict)]:
    if sort_by == SORT_LATEST:
        return sorted(lessons.items(), key=lambda item: item[1]["time_created"], reverse=True)
    elif sort_by == SORT_OLDEST:
        return sorted(lessons.items(), key=lambda item: item[1]["time_created"])
    elif sort_by == SORT_ALPHA_A_Z:
        return sorted(lessons.items(), key=lambda item: item[0])
    elif sort_by == SORT_ALPHA_Z_A:
        return sorted(lessons.items(), key=lambda item: item[0], reverse=True)
    return []

def filter_lessons(lessons: dict, search: str) -> dict:
    if search == "":
        return lessons
    else:
        return { k: v for k, v in lessons.items() if search in k or search in v["name"] }
        
# endregion Meta Management Functions

# region UI events

def on_click_sort_by(cur_sort_by: str):
    save_cache({ "cur_sort_by": cur_sort_by })
    return cur_sort_by

def on_delete_lesson(cur_lesson: str):
    delete_sheet(cur_lesson)
    delete_meta(cur_lesson)
    return ""

def on_confirm_add_lesson(old_lessons: dict, lesson_name: str):
    # generate lesson data
    sheet = generate_sheet(PATH_LESSONS / f"{lesson_name}.xlsx")

    new_lessons = old_lessons.copy()
    new_lessons[lesson_name] = create_default_meta(lesson_name, sheet)

    save_sheet(sheet)
    save_meta(new_lessons[lesson_name], override_all=True)

    return new_lessons, lesson_name

def on_click_add_lesson():
    # TODO
    return

def on_choose_lesson(meta: dict) -> tuple:
    lesson_name = meta["name"]
    print(f"Choose lesson: {lesson_name}")
    save_cache({ "cur_lesson": lesson_name })
    return lesson_name

def on_exit_lesson(lessons: dict, meta: dict) -> tuple:
    # refresh lessons list with the updated meta
    new_lessons = lessons.copy() 
    new_lessons[meta["name"]] = meta
    # reset current lesson to empty, back to the lessons list
    new_cur_lesson = ""
    save_cache({ "cur_lesson": new_cur_lesson })
    
    return new_cur_lesson, new_lessons # cur_meta is empty when no lesson is selected, back to the lessons list

def on_click_prev(meta: dict, progress_idx: int):
    meta = update_progress(meta.copy(), progress_idx - 1)
    save_meta(meta)
    return meta

def on_click_next(meta: dict, progress_idx: int):
    meta = update_progress(meta.copy(), progress_idx + 1)
    save_meta(meta)
    return meta

def on_click_submit(meta: dict, progress_idx: int, words: list[str], *inputs):
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
        new_meta = meta.copy()
        new_meta = set_pass_phrase(new_meta, progress_idx, True)
        save_meta(new_meta)
        return new_meta, message

    return meta, message

def on_click_favourite(meta: dict, progress_idx: int):
    meta = meta.copy()
    meta = toggle_phrase_favorite(meta, progress_idx)
    save_meta(meta)
    return meta

def on_click_restart(meta: dict):
    # if flag is IS_PASSED, then ignore it(delete it), 
    # else if the flags have other bits set, then just clear the IS_PASSED bit
    meta = meta.copy()
    meta["phrases_flag"] = {
        idx: flag & ~IS_PASSED
        for idx, flag in meta["phrases_flag"].items() if flag != IS_PASSED
    }
    meta["progress_idx"] = 0 # back to the first phrase
    save_meta(meta)
    return meta

# endregion UI events

# region UI Components

def render_tab_lesson(state_lessons: gr.State, state_cur_lesson: gr.State, state_cur_sort_by: gr.State, state_llm_configs: gr.State, state_cur_llm: gr.State):

    with gr.Tab("Lessons"):

        @gr.render(inputs=[state_lessons, state_cur_lesson])
        def render_tab(lessons: dict, cur_lesson: str):   

            if cur_lesson == "":
                state_search = gr.State(value="")

                # sorting bar
                with gr.Row(scale=0, elem_classes=["sort-buttons-bar"]):
                    with gr.Column(scale=0): # using column to limit the width
                        with gr.Row(scale=0, elem_classes=["sort-buttons-bar"]): # if using row, @gr.render will copy a new row inside
                            @gr.render(inputs=[state_cur_sort_by])
                            def render_tab(sort_by: str): 
                                types = [SORT_LATEST, SORT_OLDEST, SORT_ALPHA_A_Z, SORT_ALPHA_Z_A]

                                for i, v in enumerate(types):
                                    style_active = "sort-btn-active" if v == sort_by else "sort-btn-inactive"
                                    style_pos = 'sort-btn-mid'
                                    if i == 0:
                                        style_pos = 'sort-btn-left'
                                    elif i == len(types) - 1:
                                        style_pos = 'sort-btn-right'
                                
                                    b = gr.Button(v, scale=0, elem_classes=["sort-btn", style_active, style_pos], min_width=80) 
                                    b.click(on_click_sort_by, inputs=[gr.State(v)], outputs=[state_cur_sort_by])

                    t = gr.Textbox("", elem_classes=["search-box"], max_lines=1, scale=0, min_width=200, container=False, placeholder="Search")
                    t.change(lambda x: x, inputs=[t], outputs=[state_search])
                
                # list of lessons
                @gr.render(inputs=[state_lessons, state_cur_sort_by, state_search])
                def render_tab(lessons: dict, sort_by: str, search: str):
                    with gr.Row():
                        filtered_lessons = filter_lessons(lessons, search)
                        sorted_lessons = sort_lessons(filtered_lessons, sort_by)

                        for lesson_name, meta in sorted_lessons:
                            s_meta = gr.State(meta)

                            with gr.Column(variant="panel", elem_classes=["clickable-item", "lesson-item", "lesson-item-bg"], scale=0):
                                # invisible button to trigger click event for the entire item card
                                with gr.Row(scale=0, elem_classes=["lesson-name-wrapper"]):
                                    gr.Markdown(f"### {lesson_name}", elem_classes=["lesson-name"], scale=0, line_breaks=True)
                                    item_btn1 = gr.Button("", elem_classes=["lesson-click-button"])
                                    item_btn1.click(
                                        on_choose_lesson,
                                        inputs=[s_meta],
                                        outputs=[state_cur_lesson],
                                    )

                                # TODO: render meta
                                gr.Markdown(f"{meta['progress_idx']}", elem_classes=["lesson-meta"], scale=0, line_breaks=True)

                                item_btn = gr.Button("", elem_classes=["lesson-click-button"])
                                item_btn.click(
                                    on_choose_lesson,
                                    inputs=[s_meta],
                                    outputs=[state_cur_lesson],
                                )
                                
                        with gr.Column(variant="panel", elem_classes=["lesson-item"], scale=0):
                            # the last item is the add button
                            add_btn = gr.Button("➕", variant="secondary", elem_classes=["lesson-item"]) 
                            add_btn.click(on_click_add_lesson, outputs=[])

            else:
                s_cur_meta = gr.State(value=lessons[cur_lesson])
                s_cur_sheet = gr.State(value=load_sheet(cur_lesson))
                
                @gr.render(inputs=[s_cur_meta, s_cur_sheet])
                def render_lesson_content(meta: dict, sheet: gr.DataFrame):
                    progress_idx = meta["progress_idx"]
                    is_passed = is_phrase_passed(meta, progress_idx)
                    is_favourite = is_phrase_favourite(meta, progress_idx)

                    if progress_idx < 0:
                        progress_idx = 0
                    elif progress_idx >= len(sheet):
                        progress_idx = len(sheet)-1

                    with gr.Row(scale=0):
                        exit_btn = gr.Button("↩", variant="secondary", size="sm", elem_classes=["exit-button"])
                        exit_btn.click(on_exit_lesson, inputs=[state_lessons, s_cur_meta], outputs=[state_cur_lesson, state_lessons])

                        gr.Markdown(f" {meta['name']}", elem_classes=["lesson-title"])

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

                    s_progress_idx = gr.State(progress_idx)
                    s_words = gr.State(words)

                    with gr.Row(min_height=10, elem_classes=["button-bar"]):
                        with gr.Column(scale=0, min_width=50):
                            btn = gr.Button("↺")
                            btn.click(on_click_restart, inputs=[s_cur_meta], outputs=[s_cur_meta])
                        with gr.Column(scale=0, min_width=100):
                            btn = gr.Button("◀", interactive=progress_idx > 0)
                            btn.click(on_click_prev, inputs=[s_cur_meta, s_progress_idx], outputs=[s_cur_meta])
                        with gr.Column(scale=0, min_width=120):
                            submit_btn = gr.Button("⏏ submit", elem_classes=["submit-button"])
                            submit_btn.click(on_click_submit, inputs=[s_cur_meta, s_progress_idx, s_words] + inputs, outputs=[s_cur_meta, msg])
                        with gr.Column(scale=0, min_width=100):
                            btn = gr.Button("▶", interactive=progress_idx < len(sheet)-1)
                            btn.click(on_click_next, inputs=[s_cur_meta, s_progress_idx], outputs=[s_cur_meta])
                        with gr.Column(scale=0, min_width=50):
                            btn = gr.Button("★", elem_classes="favourite-on" if is_favourite else "favourite-off")
                            btn.click(on_click_favourite, inputs=[s_cur_meta, s_progress_idx], outputs=[s_cur_meta])

# endregion UI Components
