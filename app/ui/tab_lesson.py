import gradio as gr
from app.utils.paths import PATH_LESSONS
from app.utils.sheet import Sheet
import json

def get_lesson_meta(sheet: Sheet) -> dict:
    # TODO
    return {
        "test": "test", 
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
    cur_lesson = -1
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
    new_cur_lesson = lesson_name

    # check if the lesson exists
    if lesson_name not in old_lessons:
        raise ValueError(f"Lesson {lesson_name} does not exist")

    # update lesson sheet
    if old_lessons[lesson_name].get("sheet", None) is None:
        path = PATH_LESSONS / f"{lesson_name}.xlsx"
        if not path.exists():
            raise ValueError(f"Lesson {lesson_name} does not exist")

        new_lessons = old_lessons.copy()
        new_lessons[lesson_name]["sheet"] = Sheet(path)
        return new_lessons, new_cur_lesson

    return old_lessons, new_cur_lesson

def on_exit_lesson():
    return -1 # cur_lesson is -1 when no lesson is selected, back to the lessons list

def on_change_cur_llm(llm_configs: list[dict], cur_llm: int):
    cur_llm_name = "-- Not Selected --"
    if cur_llm != -1 and len(llm_configs) > cur_llm:
        cur_llm_name = llm_configs[cur_llm]["alias"]
    return cur_llm_name

# TODO
def render_tab_lesson(state_lessons: gr.State, state_cur_lesson: gr.State, state_llm_configs: gr.State, state_cur_llm: gr.State):
    with gr.Tab("Lessons") as tab_lesson:

        cur_ai = gr.Text("", label="Current AI")
        state_cur_llm.change(
            on_change_cur_llm, 
            inputs=[state_llm_configs, state_cur_llm],
            outputs=[cur_ai])

        with gr.Row():
            # list of lessons
            @gr.render(inputs=[state_lessons])
            def render_items(lessons: dict):
                
                # TODO different sorting options
                # sort lessons by name
                sorted_lessons = sorted(lessons.items(), key=lambda item: item[1]["name"])

                # render all the lesson items
                for lesson_name, lesson in sorted_lessons:
                    # data
                    meta = lesson.get("meta", None)

                    # list item: lesson entry card
                    with gr.Column(variant="panel", elem_classes=["clickable-item", "lesson-button", "lesson-item"], min_width=120, scale=0):

                        # invisible button to trigger click event for the entire item card
                        item_btn = gr.Button("", elem_classes=["lesson-click-button"])
                        item_btn.click(
                            on_choose_lesson,
                            inputs=[gr.State(lesson_name), state_lessons],
                            outputs=[state_lessons, state_cur_lesson],
                        )

                        # with gr.Row(scale=0, elem_classes="col-vert-center"):
                        gr.Markdown(f"### {lesson_name}", scale=0, height=70, min_width=120)
                        
                        gr.Markdown(f"{meta['test']}", scale=0, height=30, min_width=120)

                with gr.Column(variant="panel", elem_classes=["lesson-button"], min_width=120, scale=0):
                    # the last item is the add button
                    add_btn = gr.Button("➕", variant="secondary", elem_classes=["lesson-button"]) 
                    add_btn.click(on_click_add_lesson, inputs=[], outputs=[])
            
