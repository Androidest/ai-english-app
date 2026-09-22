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
        meta_path = PATH_LESSONS/"meta.json"
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
                cur_lesson = meta["cur_lesson"]
                lessons_meta = meta["lessons_meta"]

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

def save_lessons_meta(lessons: dict):
    if not PATH_LESSONS.exists():
        PATH_LESSONS.mkdir(parents=True, exist_ok=True)

    # save lesson meta
    new_meta = {}
    for lesson_name, lesson in lessons.items():
        new_meta[lesson_name] = lesson["meta"]

    with open(PATH_LESSONS/"meta.json", "w", encoding="utf-8") as f:
        json.dump(new_meta, f, ensure_ascii=False, indent=4)

def on_delete_lesson(old_lessons: dict, lesson_name: str):
    new_lessons = old_lessons.copy()
    del new_lessons[lesson_name]

    # update lesson files
    delete_lesson_sheet(lesson_name)
    save_lessons_meta(new_lessons)

    return new_lessons

def on_add_lesson(old_lessons: dict, lesson_name: str):
    # generate lesson data
    sheet = Sheet(PATH_LESSONS / f"{lesson_name}.xlsx", default_data={'EN':[], 'CN':[], 'ID':[]}, dtype=str)

    generate_lesson(sheet)

    new_items = old_lessons.copy()
    new_items[lesson_name] = { 
        "name": lesson_name,
        "sheet": sheet,
        "meta": get_lesson_meta(sheet),
    }

    # update lesson files
    save_lesson_sheet(new_items, lesson_name)
    save_lessons_meta(new_items)

    return new_items

def on_choose_lesson(lesson_name: str, old_lessons: dict, old_cur_lesson: str):
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

def render_tab_lesson(state_lessons: gr.State, state_curlesson: gr.State):
    with gr.Tab("Lessons") as tab_lesson:
        
        # list of lessons
        @gr.render(inputs=[state_lessons, state_curlesson])
        def render_items(items: list[dict], cur_lesson: str):
            # render all the lesson items
            for idx, item in enumerate(items):

                # data
                alias = item.get("alias", "")
                model = item.get("model", "")
                base_url = item.get("base_url", "")
                api_key = item.get("api_key", "")
                is_editing = item.get("editing", False)
                error = item.get("error", "")
                is_selected = idx == cur_llm

                # css classes for item card and button panel
                item_row_classes = ["unselected-item", "clickable-row"]
                item_btn_panel_classes = ["unselected-item", "col-vert-center"]
                if is_selected:
                    item_row_classes = ["selected-item"]
                    item_btn_panel_classes = ["selected-item-bg", "col-vert-center"]

                # item card for each llm config
                with gr.Row(variant="panel", elem_classes=item_row_classes):

                    # invisible button to trigger click event for the entire item card
                    row_click = gr.Button("", elem_classes=["row-click-button"])
                    row_click.click(
                        on_click_item,
                        inputs=[gr.State(idx), state_llm_configs,  state_cur_llm],
                        outputs=[state_cur_llm, state_llm_configs],
                    )

                    # radio circle to display the selected item
                    with gr.Column(scale=0, min_width=60, elem_classes="col-vert-center"):
                        class_name = "radio-circle selected" if is_selected else "radio-circle"
                        circle_html = gr.HTML(
                            value=f'<div class="{class_name}" data-row="{idx}"></div>',
                            elem_id=f"circle_{idx}"
                        )   

                    # llm config panel
                    with gr.Column(scale=20):
                        with gr.Row():
                            # editing mode
                            if is_editing:
                                alias_in = gr.Textbox(value=alias, label="Alias", elem_classes="input-editing", interactive=True)
                                model_in = gr.Textbox(value=model, label="Model", elem_classes="input-editing", interactive=True)
                                base_url_in = gr.Textbox(value=base_url, label="Base URL", elem_classes="input-editing", interactive=True)
                                api_key_in = gr.Textbox(value=api_key, label="API Key", elem_classes="input-editing", interactive=True)
                            
                            # non-edit mode
                            else: 
                                gr.Text(value=item.get("alias", ""), label="Alias")
                                gr.Text(value=item.get("model", ""), label="Model")
                                gr.Text(value=item.get("base_url", ""), label="Base URL")
                                gr.Text(value=item.get("api_key", ""), label="API Key")

                        if error:
                            gr.Markdown(f'<span style="color:red;">Error: {error}</span>')

                    # button panel
                    with gr.Column(scale=0, min_width=60, elem_classes=item_btn_panel_classes):
                        if not is_selected:
                            if is_editing:
                                confirm_btn = gr.Button("✅", elem_classes="confirm-editing")
                                confirm_btn.click(
                                    on_confirm_edit, 
                                    inputs=[gr.State(idx), alias_in, model_in, base_url_in, api_key_in, state_llm_configs],
                                    outputs=[state_llm_configs]
                                )

                                del_btn = gr.Button("↩", variant="secondary")
                                del_btn.click(
                                    on_cancel_edit, 
                                    inputs=[gr.State(idx), state_llm_configs], 
                                    outputs=[state_llm_configs],
                                ) 
                            else:
                                edit_btn = gr.Button("✏️", variant="secondary")
                                edit_btn.click(
                                    on_click_edit, 
                                    inputs=[gr.State(idx), state_llm_configs], 
                                    outputs=[state_llm_configs]
                                )

                                # both have delete button
                                del_btn = gr.Button("🗑️", variant="stop")
                                del_btn.click(
                                    on_delete_lesson, 
                                    inputs=[gr.State(idx), state_llm_configs], 
                                    outputs=[state_llm_configs],
                                ) 
                        else:
                            gr.Markdown('<span style="color:green; font-weight:bold;">Using</span>')


            # the last item is the add button
            add_btn = gr.Button("➕ Add", variant="secondary") 
            add_btn.click(on_add_new_item, inputs=[state_llm_configs], outputs=[state_llm_configs])

            
