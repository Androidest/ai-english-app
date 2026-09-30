import gradio as gr
from app.ui.state_llms import State_LLMs
from app.ui.state_lessons import State_Lessons, SORT_ALPHA_A_Z, SORT_ALPHA_Z_A, SORT_LATEST, SORT_OLDEST

class Tab_Lesson_List:
    def __init__(
            self, 
            state_lessons: State_Lessons, 
            state_llms: State_LLMs,
        ):

        self.state_lessons = state_lessons
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

    def on_click_sort_by(self, cur_sort_by: str):
            self.state_lessons.save_cache({ "cur_sort_by": cur_sort_by })
            return cur_sort_by
    
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
