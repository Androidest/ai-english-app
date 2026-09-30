import gradio as gr
from app.ui.confirm_dialog import ConfirmDialog
from app.ui.state_llms import State_LLMs
from app.ui.state_lessons import State_Lessons, SORT_ALPHA_A_Z, SORT_ALPHA_Z_A, SORT_LATEST, SORT_OLDEST

ERROR_TEMPLATE = "<span style='color: #e39696; font-size: 18px;'>{msg}</span>"
CORRECT_TEMPLATE = "<span style='color: #6ce38a; font-size: 35px;'>{msg}</span>"
PASSED_MSG = CORRECT_TEMPLATE.format(msg="🌟Well done!💯✅")

class Tab_Lesson:

    def __init__(self, state_lessons: State_Lessons, state_llms: State_LLMs, confirm_dialog: ConfirmDialog):

        self.state_lessons = state_lessons
        self.state_llms = state_llms

        with gr.Tab("Lessons"):

            @gr.render(inputs=[state_lessons.metas, state_lessons.cur_lesson])
            def render_tab(lessons: dict, cur_lesson: str):   

                if cur_lesson == None:
                    return

                if cur_lesson == "":
                    s_search = gr.State(value="")

                    # sorting bar
                    with gr.Row(scale=0, elem_classes=["sort-buttons-bar"]):
                        with gr.Column(scale=0): # using column to limit the width
                            with gr.Row(scale=0, elem_classes=["sort-buttons-bar"]): # if using row, @gr.render will copy a new row inside
                                @gr.render(inputs=[state_lessons.sort_by])
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
                                        b.click(self.on_click_sort_by, inputs=[gr.State(v)], outputs=[state_lessons.sort_by])

                        t = gr.Textbox("", elem_classes=["search-box"], max_lines=1, scale=0, min_width=200, container=False, placeholder="Search")
                        t.change(lambda x: x, inputs=[t], outputs=[s_search])
                    
                    # list of lessons
                    @gr.render(inputs=[state_lessons.metas, state_lessons.sort_by, s_search])
                    def render_tab(lessons: dict, sort_by: str, search: str):
                        with gr.Row():
                            filtered_lessons = state_lessons.filter_lessons(lessons, search)
                            sorted_lessons = state_lessons.sort_lessons(filtered_lessons, sort_by)

                            for lesson_name, meta in sorted_lessons:
                                s_meta = gr.State(meta)

                                with gr.Column(variant="panel", elem_classes=["clickable-item", "card-item", "card-item-bg"], scale=0):
                                    # invisible button to trigger click event for the entire item card
                                    with gr.Row(scale=0, elem_classes=["card-name-wrapper"]):
                                        gr.Markdown(f"{lesson_name}", elem_classes=["card-name"], scale=0, line_breaks=True)
                                        item_btn1 = gr.Button("", elem_classes=["card-click-button"])
                                        item_btn1.click(
                                            self.on_choose_lesson,
                                            inputs=[s_meta],
                                            outputs=[state_lessons.cur_lesson],
                                        )
                                    gr.Markdown(f"⫶☰ {meta['correct_count']}/{meta['total']}", elem_classes=["card-meta-passed"], scale=0)
                                    gr.Markdown(f"★ {meta['favourite_count']}", elem_classes=["card-meta-favourite"], scale=0)

                                    item_btn = gr.Button("", elem_classes=["card-click-button"])
                                    item_btn.click(
                                        self.on_choose_lesson,
                                        inputs=[s_meta],
                                        outputs=[state_lessons.cur_lesson],
                                    )
                                    
                            with gr.Column(variant="panel", elem_classes=["card-item"], scale=0):
                                # the last item is the add button
                                add_btn = gr.Button("➕", variant="secondary", elem_classes=["card-item"]) 
                                add_btn.click(self.on_click_add_lesson, outputs=[])

                else:
                    s_cur_meta = gr.State(value=lessons[cur_lesson])
                    s_cur_sheet = gr.State(value=state_lessons.load_sheet(cur_lesson))
                    
                    @gr.render(inputs=[s_cur_meta, s_cur_sheet])
                    def render_lesson_content(meta: dict, sheet: gr.DataFrame):
                        progress_idx = meta["progress_idx"]
                        is_passed = state_lessons.is_phrase_passed(meta, progress_idx)
                        is_favourite = state_lessons.is_phrase_favourite(meta, progress_idx)

                        if progress_idx < 0:
                            progress_idx = 0
                        elif progress_idx >= len(sheet):
                            progress_idx = len(sheet)-1

                        with gr.Row(elem_classes=["lesson-title-bar"]):
                            exit_btn = gr.Button("↩", variant="secondary", size="sm", elem_classes=["exit-button"], scale=0)
                            exit_btn.click(self.on_exit_lesson, inputs=[state_lessons.metas, s_cur_meta], outputs=[state_lessons.metas, state_lessons.cur_lesson])

                            gr.Markdown(f"{meta['name']}", scale=1, elem_classes=["lesson-title"])
                            gr.Textbox(f"Page: {progress_idx+1}", scale=0, elem_classes=["lesson-meta"], max_lines=1, container=False)
                            gr.Textbox(f"⫶☰ Passed: {meta['correct_count']} / {meta['total']}", scale=0, elem_classes=["lesson-meta"], max_lines=1, container=False)
                            gr.Textbox(f"★ Favourite: {meta['favourite_count']}", scale=0, elem_classes=["lesson-meta"], max_lines=1, container=False)

                            btn = gr.Button("⛔", scale=0, elem_classes=["lesson-delete-btn"])
                            confirm_dialog.attach(
                                    trigger=btn, 
                                    
                                    message=f"Are you sure you want to delete <br>\"<span>{meta['name']}</span>\" ? <br>This action cannot be undone!",
                                    confirm_text="Delete",
                                    cancel_text="Cancel",
                                    danger=True,

                                    confirm_fn=self.on_delete_lesson, 
                                    confirm_inputs=[state_lessons.metas, s_cur_meta],
                                    confirm_outputs=[state_lessons.metas, state_lessons.cur_lesson], 
                                )

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
                                btn.click(self.on_click_restart, inputs=[s_cur_meta], outputs=[s_cur_meta])
                            with gr.Column(scale=0, min_width=100):
                                btn = gr.Button("◀", interactive=progress_idx > 0)
                                btn.click(self.on_click_prev, inputs=[s_cur_meta, s_progress_idx], outputs=[s_cur_meta])
                            with gr.Column(scale=0, min_width=120):
                                submit_btn = gr.Button("⏏ submit", elem_classes=["submit-button"])
                                submit_btn.click(self.on_click_submit, inputs=[s_cur_meta, s_progress_idx, s_words] + inputs, outputs=[s_cur_meta, msg])
                            with gr.Column(scale=0, min_width=100):
                                btn = gr.Button("▶", interactive=progress_idx < len(sheet)-1)
                                btn.click(self.on_click_next, inputs=[s_cur_meta, s_progress_idx], outputs=[s_cur_meta])
                            with gr.Column(scale=0, min_width=50):
                                btn = gr.Button("★", elem_classes="favourite-on" if is_favourite else "favourite-off")
                                btn.click(self.on_click_favourite, inputs=[s_cur_meta, s_progress_idx], outputs=[s_cur_meta])

    # region UI events

    def on_click_sort_by(self, cur_sort_by: str):
        self.state_lessons.save_cache({ "cur_sort_by": cur_sort_by })
        return cur_sort_by

    def on_delete_lesson(self, lessons: dict, meta: dict) -> tuple:
        new_cur_lesson = "" # deselect the current lesson, back to the lessons list
        lesson_name = meta["name"]
        new_lessons = lessons.copy() 
        del new_lessons[lesson_name]
        self.state_lessons.delete_sheet(lesson_name)
        self.state_lessons.delete_meta(lesson_name)
        self.state_lessons.save_cache({ "cur_lesson": new_cur_lesson })
        gr.Info(f"⛔ Lesson {lesson_name} deleted successfully! ⛔")

        return new_lessons, new_cur_lesson

    def on_confirm_add_lesson(self, old_lessons: dict, lesson_name: str):
        # generate lesson data
        sheet = self.state_lessons.generate_sheet(lesson_name)

        new_lessons = old_lessons.copy()
        new_lessons[lesson_name] = self.state_lessons.create_default_meta(lesson_name, sheet)

        self.state_lessons.save_sheet(sheet)
        self.state_lessons.save_meta(new_lessons[lesson_name], override_all=True)

        return new_lessons, lesson_name

    def on_click_add_lesson(self):
        # TODO
        return

    def on_choose_lesson(self, meta: dict) -> tuple:
        lesson_name = meta["name"]
        print(f"Choose lesson: {lesson_name}")
        self.state_lessons.save_cache({ "cur_lesson": lesson_name })
        return lesson_name

    def on_exit_lesson(self, lessons: dict, meta: dict) -> tuple:
        # refresh lessons list with the updated meta
        new_lessons = lessons.copy() 
        new_lessons[meta["name"]] = meta
        # reset current lesson to empty, back to the lessons list
        new_cur_lesson = ""
        self.state_lessons.save_cache({ "cur_lesson": new_cur_lesson })
        
        return new_lessons, new_cur_lesson # cur_meta is empty when no lesson is selected, back to the lessons list

    def on_click_prev(self, meta: dict, progress_idx: int):
        meta = self.state_lessons.update_progress(meta.copy(), progress_idx - 1)
        self.state_lessons.save_meta(meta)
        return meta

    def on_click_next(self, meta: dict, progress_idx: int):
        meta = self.state_lessons.update_progress(meta.copy(), progress_idx + 1)
        self.state_lessons.save_meta(meta)
        return meta

    def on_click_submit(self, meta: dict, progress_idx: int, words: list[str], *inputs):
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
            new_meta = self.state_lessons.set_pass_phrase(new_meta, progress_idx, True)
            new_meta = self.state_lessons.make_brief_meta(new_meta)
            self.state_lessons.save_meta(new_meta)
            return new_meta, message

        return meta, message

    def on_click_favourite(self, meta: dict, progress_idx: int):
        meta = meta.copy()
        meta = self.state_lessons.toggle_phrase_favorite(meta, progress_idx)
        meta = self.state_lessons.make_brief_meta(meta)
        self.state_lessons.save_meta(meta)
        return meta

    def on_click_restart(self, meta: dict):
        # if flag is IS_PASSED, then ignore it(delete it), 
        # else if the flags have other bits set, then just clear the IS_PASSED bit
        meta = meta.copy()
        meta = self.state_lessons.reset_meta(meta)
        self.state_lessons.save_meta(meta)
        return meta

    # endregion UI events
