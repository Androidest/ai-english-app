import gradio as gr
import random
import asyncio

from app.ui.dialogs.confirm_dialog import ConfirmDialog
from app.ui.dialogs.lesson_gen_info_dialog import LessonGenInfoDialog
from app.ui.models.cache import Cache
from app.ui.models.meta import Meta
from app.ui.states.state_tts import State_TTS
from app.ui.states.state_lesson import State_Lesson, FAV_LESSON
from app.utils.sheet import Sheet
from app.workflow._core_.tts_config import TTSConfig
from app.utils.paths import PATH_AUDIO

ERROR_TEMPLATE = "<span style='color: #e39696; font-size: 18px;'>{msg}</span>"
CORRECT_TEMPLATE = "<span style='color: #6ce38a; font-size: 35px;'>{msg}</span>"
PASSED_MSG = CORRECT_TEMPLATE.format(msg="🌟Well done!💯✅")

class Tab_Lesson_Chosen:
    def __init__(
            self, 
            state_lesson: State_Lesson, 
            state_tts: State_TTS, 
            confirm_dialog: ConfirmDialog, 
            metas:dict[str, Meta], 
            cur_lesson:str,
            lesson_gen_info_dialog: LessonGenInfoDialog,
        ):

        self.state_lesson = state_lesson
        self.state_tts = state_tts

        s_cur_meta = gr.State(value=metas[cur_lesson])
        s_cur_sheet = gr.State(value=state_lesson.load_sheet(cur_lesson))
        
        @gr.render(inputs=[s_cur_meta, s_cur_sheet])
        def render_lesson_content(meta: Meta, sheet: Sheet):
            total = max(meta.total, 1)
            progress_idx = meta.progress_idx
            correct_percent = max(meta.correct_count / total * 100, 0)
            page_percent = max((meta.progress_idx + 1) / total * 100, 0)
            is_passed = state_lesson.is_phrase_passed(meta, progress_idx)
            is_favourite = state_lesson.is_phrase_favourite(meta, progress_idx)
            s_progress_idx = gr.State(progress_idx)
            is_FAV_LESSON = meta.name == FAV_LESSON

            if progress_idx >= len(sheet):
                progress_idx = len(sheet)-1
            if progress_idx < 0:
                progress_idx = 0

            with gr.Row(elem_classes=["progress-bar-track"]):
                gr.HTML(f'''
                <div class="progress-bar-fill" style="width: {correct_percent}% !important;"></div>
                <div class="progress-bar-fill-2" style="width: {page_percent}% !important;"></div>
                ''')

            with gr.Row(elem_classes=["lesson-title-bar"]):
                exit_btn = gr.Button("↩", variant="secondary", size="sm", elem_classes=["exit-button"], scale=0)
                exit_btn.click(
                    self.on_exit_lesson, 
                    inputs=[state_lesson.metas, s_cur_meta, state_lesson.pending_uppdate_meta], 
                    outputs=[state_lesson.metas, state_lesson.cur_lesson, state_lesson.pending_uppdate_meta]
                )

                if is_FAV_LESSON:
                    gr.Markdown(f"{meta.name}", scale=1, elem_classes=["lesson-title", "fav-title" ])
                else:
                    with gr.Column(scale=0, min_width=40):
                        rename = gr.Button("✏️", elem_id="rename-btn")
                    
                    gr.Markdown(f"{meta.name}", scale=1, elem_classes=["lesson-title"])
                    gr.Textbox(f"Learning: {meta.gen_params.source_language}", scale=0, elem_classes=["lesson-meta"], max_lines=1, container=False)
                    gr.Textbox(f"Difficulty: {meta.gen_params.difficulty}", scale=0, elem_classes=["lesson-meta"], max_lines=1, container=False)
                
                gr.Textbox(f"Page: {progress_idx+1}", scale=0, elem_classes=["lesson-meta"], max_lines=1, container=False)
                gr.Textbox(f"⫶☰ Passed: {meta.correct_count} / {meta.total}", scale=0, elem_classes=["lesson-meta"], max_lines=1, container=False)
                gr.Textbox(f"★ Favourite: {meta.favourite_count}", scale=0, elem_classes=["lesson-meta"], max_lines=1, container=False)

                if not is_FAV_LESSON:
                    btn = gr.Button("⛔", scale=0, elem_classes=["lesson-delete-btn"])
                    confirm_dialog.attach(
                            trigger=btn, 
                            
                            message=f"Are you sure you want to delete <br>\"<span>{meta.name}</span>\" ? <br>This action cannot be undone!",
                            confirm_text="Delete",
                            cancel_text="Cancel",
                            danger=True,

                            confirm_fn=self.on_delete_lesson, 
                            confirm_inputs=[state_lesson.metas, s_cur_meta],
                            confirm_outputs=[state_lesson.metas, state_lesson.cur_lesson], 
                        )

            if len(sheet) == 0:
                with gr.Row():
                    with gr.Column(elem_classes=["empty-lesson-wrapper"]):
                        gr.Markdown(f"-- There's nothing here yet. --", elem_classes=["empty-lesson"], scale=0, min_width=10)
                return

            inputs = []
            with gr.Row():
                with gr.Column(elem_classes=["lesson-content"]):
                    src = sheet[progress_idx, "SRC"]
                    display_lang_1 = sheet[progress_idx, "DIS_1"]
                    display_lang_2 = sheet[progress_idx, "DIS_2"]

                    if type(display_lang_1) is str and display_lang_1 != "":
                        gr.Markdown(f"{display_lang_1}", elem_classes=["phrase"], scale=0, min_width=10)
                    if type(display_lang_2) is str and display_lang_2 != "":
                        gr.Markdown(f"{display_lang_2}", elem_classes=["phrase"], scale=0, min_width=10)

                    words = []
                    all = []
                    with gr.Row(elem_classes=["phrase-src"]) as row:
                        for i, word in enumerate(src.split(' ')):
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
                if not is_FAV_LESSON:
                    with gr.Column(scale=0, min_width=50):
                        info_btn = gr.Button("🛈︎")
                        lesson_gen_info_dialog.attach(info_btn)
                with gr.Column(scale=0, min_width=50):
                    btn = gr.Button("↺")
                    btn.click(self.on_click_restart, inputs=[s_cur_meta], outputs=[s_cur_meta])
                with gr.Column(scale=0, min_width=100):
                    prev_btn = gr.Button("◀", interactive=progress_idx > 0)
                with gr.Column(scale=0, min_width=120):
                    submit_btn = gr.Button("⏏ submit", elem_classes=["submit-button"])
                with gr.Column(scale=0, min_width=100):
                    next_btn = gr.Button("▶", interactive=progress_idx < len(sheet)-1)
                with gr.Column(scale=0, min_width=50):
                    if not is_FAV_LESSON:
                        btn = gr.Button("★", elem_classes="favourite-on" if is_favourite else "favourite-off")
                        btn.click(
                            self.on_click_favourite_origin, 
                            inputs=[s_cur_meta, s_progress_idx, s_cur_sheet, self.state_lesson.pending_uppdate_meta], 
                            outputs=[s_cur_meta, self.state_lesson.pending_uppdate_meta]
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
                            confirm_inputs=[s_cur_meta, s_progress_idx, s_cur_sheet, state_lesson.pending_uppdate_meta], 
                            confirm_outputs=[s_cur_meta, state_lesson.pending_uppdate_meta, s_cur_sheet, s_progress_idx]
                        )

                with gr.Column(scale=0, min_width=50):
                    hint = gr.Button("💡")

            with gr.Row(min_height=10, elem_classes=["button-bar"]):
                with gr.Column(scale=0, min_width=150):
                    speak = gr.Button("🕪 read", visible=is_passed)
                with gr.Column(scale=0, min_width=150):
                    regenerate_speak = gr.Button("🕪 re-generate", visible=is_passed, interactive=False)

            audio_out = gr.Audio(
                label="", 
                interactive=False, 
                autoplay=True, 
                show_label=False, 
                container=False,
                editable=False,
                buttons=[],
            )

            s_words = gr.State(words)

            confirm_dialog.attach(
                trigger=rename,

                textbox=meta.name,
                
                message=f"Rename current lesson",
                confirm_text="Confirm",
                cancel_text="Cancel",
                danger=True,

                confirm_fn=self.on_rename_lesson, 
                confirm_inputs=[s_cur_meta, s_cur_sheet, state_lesson.metas],
                confirm_outputs=[s_cur_meta, state_lesson.metas, state_lesson.cur_lesson], 
            )

            # hint
            hint.click(
                self.on_click_hint,
                inputs=[s_words, *inputs],
                outputs=[hint, *inputs],
                show_progress="hidden",
            )

            # speak
            speak.click(
                self.on_click_speak,
                inputs=[gr.State(src), state_tts.configs, state_tts.cur_model, gr.State(False)],
                outputs=[audio_out, speak, regenerate_speak],
                show_progress="hidden",
            )

            regenerate_speak.click(
                self.on_click_speak,
                inputs=[gr.State(src), state_tts.configs, state_tts.cur_model, gr.State(True)],
                outputs=[audio_out, speak, regenerate_speak],
                show_progress="hidden",
            )

            audio_out.pause(
                self.on_audio_pause,
                outputs=[audio_out, speak, regenerate_speak],
                show_progress="hidden",
            )

            # prev and next
            prev_btn.click(
                self.on_click_prev, 
                inputs=[s_cur_meta, s_progress_idx], 
                outputs=[s_cur_meta, audio_out, regenerate_speak],
                show_progress=False,
            )
            next_btn.click(
                self.on_click_next, 
                inputs=[s_cur_meta, s_progress_idx], 
                outputs=[s_cur_meta, audio_out, regenerate_speak],
                show_progress=False,
            )
            
            # submit events
            for input in inputs:
                input.submit(
                    self.on_click_submit, 
                    inputs=[s_cur_meta, s_progress_idx, msg, s_words, *inputs], 
                    outputs=[s_cur_meta, msg]
                )
                
            submit_btn.click(
                self.on_click_submit, 
                inputs=[s_cur_meta, s_progress_idx, msg, s_words, *inputs], 
                outputs=[s_cur_meta, msg]
            )

    def on_exit_lesson(self, lessons: dict, meta: Meta, pending_update_meta:tuple) -> tuple:
        # refresh lessons list with the updated meta
        new_lessons = lessons.copy() 
        new_lessons[meta.name] = meta

        # update all the pending meta that are changed by setting Favourites
        if len(pending_update_meta) > 0:
            for name in pending_update_meta:
                new_lessons[name] = self.state_lesson.load_meta(name)

        # reset current lesson to empty, back to the lessons list
        new_cur_lesson = ""
        self.state_lesson.save_cache(
            cur_lesson=new_cur_lesson
        )
        
        return new_lessons, new_cur_lesson, () # cur_meta is empty when no lesson is selected, back to the lessons list

    def on_rename_lesson(
        self, 
        meta: Meta,
        sheet: Sheet,
        metas: dict[str, Meta],
        new_name: str,
    ) -> tuple:

        old_name = meta.name
        self.state_lesson.rename_sheet(sheet, new_name)
        meta = self.state_lesson.rename_meta(meta, new_name)

        new_metas = {
            k: v
            for k, v in metas.items()
            if k != old_name
        }
        new_metas[meta.name] = meta

        gr.Info(f"Renamed Lesson `{old_name}` to `{new_name}`")
        return meta, new_metas, meta.name
    
    def on_delete_lesson(
        self, 
        lessons: dict[str, Meta], 
        meta: Meta
    ) -> tuple:
        
        new_cur_lesson = "" # deselect the current lesson, back to the lessons list
        lesson_name = meta.name
        new_lessons = lessons.copy() 
        del new_lessons[lesson_name]
        self.state_lesson.delete_sheet(lesson_name)
        self.state_lesson.delete_meta(lesson_name)
        self.state_lesson.save_cache(
            cur_lesson = new_cur_lesson,
        )
        gr.Info(f"⛔ Lesson {lesson_name} deleted successfully! ⛔")

        return new_lessons, new_cur_lesson
    
    def on_click_prev(self, meta: Meta, progress_idx: int):
        meta = self.state_lesson.update_progress(meta.model_copy(), progress_idx - 1)
        meta = self.state_lesson.save_meta(meta)
        return meta, None, gr.update(interactive=False)

    def on_click_next(self, meta: Meta, progress_idx: int):
        meta = self.state_lesson.update_progress(meta.model_copy(), progress_idx + 1)
        meta = self.state_lesson.save_meta(meta)
        return meta, None, gr.update(interactive=False)

    def on_click_submit(self, meta: Meta, progress_idx: int, old_msg: str, words: list[str], *inputs):
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
            new_meta = meta.model_copy()
            if old_msg != PASSED_MSG:
                message = PASSED_MSG
                new_meta = self.state_lesson.set_pass_phrase(new_meta, progress_idx, True)
                new_meta = self.state_lesson.make_brief_meta(new_meta)
                new_meta = self.state_lesson.save_meta(new_meta)
                return new_meta, message
            else:
                # If this page is already passed, this `submit` will switch to the next page.   
                new_meta = self.state_lesson.update_progress(new_meta, progress_idx + 1)
                new_meta = self.state_lesson.save_meta(new_meta)
                return new_meta, gr.skip()

        return meta, message

    def on_click_favourite_origin(self, origin_meta: Meta, progress_idx: int, sheet: Sheet, pendind_update_meta: tuple):
        origin_meta = origin_meta.model_copy()
        if not self.state_lesson.is_phrase_favourite(origin_meta, progress_idx):
            self.state_lesson.save_favourite(
                val=sheet[progress_idx].to_dict(),
                meta=origin_meta, 
                idx=progress_idx,
            )

        else:
            self.state_lesson.delete_favourite(
                en_key=sheet[progress_idx, "SRC"],
                meta=origin_meta,
                idx=progress_idx,
                is_origin=True,
            )

        pendind_update_meta = (*pendind_update_meta, FAV_LESSON)
        return origin_meta, pendind_update_meta

    def on_delete_favourite(self, fav_meta: Meta, progress_idx: int, fav_sheet: Sheet, pendind_update_meta: tuple):
        fav_meta = fav_meta.model_copy()
        fav_sheet, pending_origin = self.state_lesson.delete_favourite(
            en_key=fav_sheet[progress_idx, "SRC"],
            meta=fav_meta,
            idx=progress_idx,
            is_origin=False,
        )
        if pending_origin != None:
            pendind_update_meta = (*pendind_update_meta, pending_origin)

        return fav_meta, pendind_update_meta, fav_sheet, progress_idx

    def on_click_restart(self, meta: Meta):
        # if flag is IS_PASSED, then ignore it(delete it), 
        # else if the flags have other bits set, then just clear the IS_PASSED bit
        meta = meta.model_copy()
        meta = self.state_lesson.reset_meta(meta)
        meta = self.state_lesson.save_meta(meta)
        return meta

    async def on_click_hint(
        self, 
        words: list[str], 
        *inputs: list[str],
    ):
        candidate = []
        for i, (word, in_word) in enumerate(zip(words, inputs)):
            if word != in_word:
                candidate.append((i, word))

        if not candidate:
            yield (
                gr.update(interactive=True), 
                *([gr.skip()]*len(inputs)),
            )
            return

        chosen_word = random.sample(candidate, 1)
        out_inputs = [ gr.update(interactive=False) ] * len(inputs)
        for (i, word) in chosen_word:
            masked_word = self.state_lesson.random_mask_word(word, mask_ratio=0.6)
            out_inputs[i] = gr.update(value=masked_word, interactive=False, elem_id="word-wrapper")

        yield (
            gr.update(interactive=False), 
            *out_inputs,
        )

        await asyncio.sleep(3)

        out_inputs = []
        for i, in_word in enumerate(inputs):
            out_inputs.append(gr.update(value=in_word, interactive=True, elem_id=""))

        yield (
            gr.update(interactive=True), 
            *out_inputs,
        )

    async def on_click_speak(
        self,
        src_sentence: str,
        tts_configs: list[TTSConfig],
        cur_model: int,
        regenerate: bool,
    ):
        yield (
            gr.update(value=None, playback_position=0), 
            gr.update(interactive=False),
            gr.update(interactive=False),
        )
        await asyncio.sleep(0.02)
        
        if cur_model < 0 or cur_model >= len(tts_configs):
            gr.Warning("Currently, no TTS model is selected!")
            return

        model_config = tts_configs[cur_model]
        filepath = PATH_AUDIO/f"{src_sentence}.{model_config.voice_id}.wav"

        if not filepath.exists() or regenerate:
            from app.workflow._core_.tts_runtime import TTSRuntime
            runtime = TTSRuntime(model_config)
            model = runtime.get_model()
            data = model.synthesize(src_sentence)
            yield (
                gr.update(value=data, playback_position=0), 
                gr.skip(),
                gr.skip(),
            )
            runtime.save_audio(data, filepath)
            return

        # switch between filepath and ndarray data to force the audio component to replay the content
        yield (
            gr.update(value=filepath, playback_position=0), 
            gr.skip(),
            gr.skip(),
        )

    def on_audio_pause(self):
        return (
            gr.update(playback_position=0),
            gr.update(interactive=True), 
            gr.update(interactive=True), 
        )
    
