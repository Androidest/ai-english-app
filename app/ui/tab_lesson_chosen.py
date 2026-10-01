import gradio as gr
from app.ui.confirm_dialog import ConfirmDialog
from app.ui.state_llms import State_LLMs
from app.ui.state_lessons import State_Lessons, FAV_LESSON
from app.utils.sheet import Sheet

ERROR_TEMPLATE = "<span style='color: #e39696; font-size: 18px;'>{msg}</span>"
CORRECT_TEMPLATE = "<span style='color: #6ce38a; font-size: 35px;'>{msg}</span>"
PASSED_MSG = CORRECT_TEMPLATE.format(msg="🌟Well done!💯✅")

class Tab_Lesson_Chosen:
    def __init__(
            self, 
            state_lessons: State_Lessons, 
            state_llms: State_LLMs, 
            confirm_dialog: ConfirmDialog, 
            metas:list[dict], 
            cur_lesson:str,
        ):

        self.state_lessons = state_lessons

        s_cur_meta = gr.State(value=metas[cur_lesson])
        s_cur_sheet = gr.State(value=state_lessons.load_sheet(cur_lesson))
        
        @gr.render(inputs=[s_cur_meta, s_cur_sheet])
        def render_lesson_content(meta: dict, sheet: Sheet):
            total = max(meta["total"], 1)
            progress_idx = meta["progress_idx"]
            correct_percent = max(meta['correct_count'] / total * 100, 0)
            page_percent = max((meta['progress_idx'] + 1) / total * 100, 0)
            is_passed = state_lessons.is_phrase_passed(meta, progress_idx)
            is_favourite = state_lessons.is_phrase_favourite(meta, progress_idx)
            s_progress_idx = gr.State(progress_idx)
            is_FAV_LESSON = meta["name"] == FAV_LESSON

            if progress_idx < 0:
                progress_idx = 0
            elif progress_idx >= len(sheet):
                progress_idx = len(sheet)-1            

            with gr.Row(elem_classes=["progress-bar-track"]):
                gr.HTML(f'''
                <div class="progress-bar-fill" style="width: {correct_percent}% !important;"></div>
                <div class="progress-bar-fill-2" style="width: {page_percent}% !important;"></div>
                ''')

            with gr.Row(elem_classes=["lesson-title-bar"]):
                exit_btn = gr.Button("↩", variant="secondary", size="sm", elem_classes=["exit-button"], scale=0)
                exit_btn.click(
                    self.on_exit_lesson, 
                    inputs=[state_lessons.metas, s_cur_meta, state_lessons.pending_uppdate_meta], 
                    outputs=[state_lessons.metas, state_lessons.cur_lesson, state_lessons.pending_uppdate_meta]
                )

                if is_FAV_LESSON:
                    gr.Markdown(f"{meta['name']}", scale=1, elem_classes=["lesson-title", "fav-title" ])
                else:
                    gr.Markdown(f"{meta['name']}", scale=1, elem_classes=["lesson-title"])
                gr.Textbox(f"Page: {progress_idx+1}", scale=0, elem_classes=["lesson-meta"], max_lines=1, container=False)
                gr.Textbox(f"⫶☰ Passed: {meta['correct_count']} / {meta['total']}", scale=0, elem_classes=["lesson-meta"], max_lines=1, container=False)
                gr.Textbox(f"★ Favourite: {meta['favourite_count']}", scale=0, elem_classes=["lesson-meta"], max_lines=1, container=False)

                if not is_FAV_LESSON:
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

            if len(sheet) == 0:
                with gr.Row():
                    with gr.Column(elem_classes=["empty-lesson-wrapper"]):
                        gr.Markdown(f"-- There's nothing here yet. --", elem_classes=["empty-lesson"], scale=0, min_width=10)
                return

            inputs = []
            with gr.Row():
                with gr.Column(elem_classes=["lesson-content"]):
                    en = sheet[progress_idx, "EN"]
                    cn = sheet[progress_idx, "CN"]
                    id = sheet[progress_idx, "ID"]
                    
                    gr.Markdown(f"{cn}", elem_classes=["phrase"], scale=0, min_width=10)
                    gr.Markdown(f"{id}", elem_classes=["phrase"], scale=0, min_width=10)

                    words = []
                    all = []
                    with gr.Row(elem_classes=["phrase-en"]) as row:
                        for i, word in enumerate(en.split(' ')):
                            word = word.strip()
                            punctuation = ""

                            if not word[-1].isalpha() and word[-1] != "'":
                                punctuation = word[-1]
                                word = word[:-1]

                            words.append(word)
                            all.append(word)

                            input = gr.Textbox(
                                word if is_passed else "", 
                                max_lines=1, 
                                scale=0, 
                                min_width=10, 
                                container=False, 
                                elem_classes=["word", "text-input"], 
                                interactive=True, 
                                max_length=len(word)
                            )

                            inputs.append(input)
                            
                            if punctuation != "":
                                all.append(punctuation)
                                gr.Textbox(
                                    punctuation, 
                                    max_lines=1, 
                                    scale=0, 
                                    min_width=10, 
                                    container=False, 
                                    elem_classes=["word", "word-punct"], 
                                    interactive=False
                                )

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
                    btn.click(self.on_click_restart, inputs=[s_cur_meta], outputs=[s_cur_meta])
                with gr.Column(scale=0, min_width=100):
                    btn = gr.Button("◀", interactive=progress_idx > 0)
                    btn.click(self.on_click_prev, inputs=[s_cur_meta, s_progress_idx], outputs=[s_cur_meta])
                with gr.Column(scale=0, min_width=120):
                    submit_btn = gr.Button("⏏ submit", elem_classes=["submit-button"])
                with gr.Column(scale=0, min_width=100):
                    btn = gr.Button("▶", interactive=progress_idx < len(sheet)-1)
                    btn.click(self.on_click_next, inputs=[s_cur_meta, s_progress_idx], outputs=[s_cur_meta])
                with gr.Column(scale=0, min_width=50):
                    if not is_FAV_LESSON:
                        btn = gr.Button("★", elem_classes="favourite-on" if is_favourite else "favourite-off")
                        btn.click(
                            self.on_click_favourite_origin, 
                            inputs=[s_cur_meta, s_progress_idx, s_cur_sheet, self.state_lessons.pending_uppdate_meta], 
                            outputs=[s_cur_meta, self.state_lessons.pending_uppdate_meta]
                        )
                    else:
                        btn = gr.Button("★", elem_classes="favourite-on")
                        confirm_dialog.attach(
                            trigger=btn,

                            message="Are you sure you want to remove this from <br><span>'Favourite'?</span>",
                            confirm_text="Sure",
                            cancel_text="Cancel",
                            danger=True,

                            confirm_fn=self.on_delete_favourite, 
                            confirm_inputs=[s_cur_meta, s_progress_idx, s_cur_sheet, state_lessons.pending_uppdate_meta], 
                            confirm_outputs=[s_cur_meta, state_lessons.pending_uppdate_meta, s_cur_sheet, s_progress_idx]
                        )

            # submit events
            s_words = gr.State(words)
            for input in inputs:
                input.submit(
                    self.on_click_submit, 
                    inputs=[s_cur_meta, s_progress_idx, s_words] + inputs, 
                    outputs=[s_cur_meta, msg]
                )
                
            submit_btn.click(
                self.on_click_submit, 
                inputs=[s_cur_meta, s_progress_idx, s_words] + inputs, 
                outputs=[s_cur_meta, msg]
            )

    def on_exit_lesson(self, lessons: dict, meta: dict, pending_update_meta:tuple) -> tuple:
        # refresh lessons list with the updated meta
        new_lessons = lessons.copy() 
        new_lessons[meta["name"]] = meta

        # update all the pending meta that are changed by setting Favourites
        if len(pending_update_meta) > 0:
            for name in pending_update_meta:
                new_lessons[name] = self.state_lessons.load_meta(name)

        # reset current lesson to empty, back to the lessons list
        new_cur_lesson = ""
        self.state_lessons.save_cache({ "cur_lesson": new_cur_lesson })
        
        return new_lessons, new_cur_lesson, () # cur_meta is empty when no lesson is selected, back to the lessons list

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

    def on_click_favourite_origin(self, origin_meta: dict, progress_idx: int, sheet: Sheet, pendind_update_meta: tuple):
        origin_meta = origin_meta.copy()
        if not self.state_lessons.is_phrase_favourite(origin_meta, progress_idx):
            self.state_lessons.save_favourite(
                val=sheet[progress_idx].to_dict(),
                meta=origin_meta, 
                idx=progress_idx,
            )

        else:
            self.state_lessons.delete_favourite(
                en_key=sheet[progress_idx, "EN"],
                meta=origin_meta,
                idx=progress_idx,
                is_origin=True,
            )

        pendind_update_meta = (*pendind_update_meta, FAV_LESSON)
        return origin_meta, pendind_update_meta

    def on_delete_favourite(self, fav_meta: dict, progress_idx: int, fav_sheet: Sheet, pendind_update_meta: tuple):
        fav_meta = fav_meta.copy()
        fav_sheet, pending_origin = self.state_lessons.delete_favourite(
            en_key=fav_sheet[progress_idx, "EN"],
            meta=fav_meta,
            idx=progress_idx,
            is_origin=False,
        )
        if pending_origin != None:
            pendind_update_meta = (*pendind_update_meta, pending_origin)

        if progress_idx >= len(fav_sheet):
            progress_idx = len(fav_sheet)-1
            self.state_lessons.update_progress(fav_meta, progress_idx)

        return fav_meta, pendind_update_meta, fav_sheet, progress_idx

    def on_click_restart(self, meta: dict):
        # if flag is IS_PASSED, then ignore it(delete it), 
        # else if the flags have other bits set, then just clear the IS_PASSED bit
        meta = meta.copy()
        meta = self.state_lessons.reset_meta(meta)
        self.state_lessons.save_meta(meta)
        return meta
