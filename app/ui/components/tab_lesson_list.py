import gradio as gr
from app.ui.models.cache import Cache
from app.ui.models.meta import Meta
from app.ui.states.state_llms import State_LLMs
from app.ui.states.state_lessons import (
    State_Lessons, 
    SORTING_OPTIONS, 
    FAV_LESSON,
)
from app.ui.dialogs.gen_lesson_dialog import GenLessonDialog

class Tab_Lesson_List:
    def __init__(
            self, 
            state_lessons: State_Lessons, 
            gen_lesson_dialog: GenLessonDialog,
        ):

        self.state_lessons = state_lessons
        s_search = gr.State(value="")
        
        # Sorting and search bar
        with gr.Row(scale=0, elem_classes=["sort-buttons-bar"]):

            # Sorting
            with gr.Column(scale=0): # using column to limit the width
                with gr.Row(scale=0, elem_classes=["sort-buttons-bar"]): # if using row, @gr.render will copy a new row inside
                    @gr.render(inputs=[state_lessons.sort_by])
                    def render_tab(sort_by: str): 
                        types = SORTING_OPTIONS.__args__

                        for i, option in enumerate(types):
                            style_active = "sort-btn-active" if option == sort_by else "sort-btn-inactive"
                            style_pos = 'sort-btn-mid'
                            if i == 0:
                                style_pos = 'sort-btn-left'
                            elif i == len(types) - 1:
                                style_pos = 'sort-btn-right'
                        
                            b = gr.Button(value=option, scale=0, elem_classes=["sort-btn", style_active, style_pos], min_width=80) 
                            b.click(self.on_click_sort_by, inputs=[gr.State(option)], outputs=[state_lessons.sort_by])

            # Search box
            t = gr.Textbox("", elem_classes=["search-box"], max_lines=1, scale=0, min_width=200, container=False, placeholder="Search")
            t.change(lambda x: x, inputs=[t], outputs=[s_search])
        
        # list of lessons
        @gr.render(inputs=[state_lessons.metas, state_lessons.sort_by, s_search])
        def render_tab(lessons: dict[str, Meta], sort_by: str, search: str):
            with gr.Row():

                # Reorganize lessons, including sorting and filtering
                sorted_lessons = state_lessons.reorganize_lessons(
                    lessons,
                    sort_by, 
                    search,
                )

                # Iterate through all lessons and display them as cards
                for meta in sorted_lessons:
                    s_meta = gr.State(meta)
                    lesson_name = meta.name

                    # Card item
                    with gr.Column(variant="panel", elem_id="card-item", scale=0):

                        # Difficulty on the top right.
                        if lesson_name != FAV_LESSON:
                            gr.HTML(value=f'{meta.gen_params.difficulty}', elem_id=f"card-difficulty-{meta.gen_params.difficulty}")
                        
                        # Card title = lesson name
                        with gr.Row(scale=0, elem_classes=["card-name-wrapper"]):
                            if lesson_name != FAV_LESSON:
                                gr.Markdown(lesson_name, elem_classes=["card-name"], scale=0, line_breaks=True)
                            else:
                                gr.Markdown(f"<span style='font-size:30px;'>🌟</span><br>{lesson_name}", elem_classes=["card-name"], scale=0, line_breaks=True)

                        # Meta information
                        gr.Markdown(f"{meta.gen_params.source_language}", elem_id="card-meta-lang", scale=0)
                        gr.Markdown(f"⫶☰ {meta.correct_count}/{meta.total}", elem_id="card-meta-inf", scale=0)
                        if lesson_name != FAV_LESSON:
                            gr.Markdown(f"★ {meta.favourite_count}", elem_id="card-meta-fav", scale=0)

                        # An invisible button covers the entire card to trigger the card's click event.
                        item_btn = gr.Button("", elem_id="card-click-button")
                        item_btn.click(
                            self.on_choose_lesson,
                            inputs=[s_meta],
                            outputs=[state_lessons.cur_lesson],
                        )

                # "+": The add button. The last item of the list 
                with gr.Column(variant="panel", elem_id="card-item-fav", scale=0):
                    add_btn = gr.Button("➕", variant="secondary", elem_id="card-click-button-fav") 
                    gen_lesson_dialog.attach(add_btn)

    def on_click_sort_by(self, cur_sort_by: str):
        self.state_lessons.save_cache(
            cur_sort_by = cur_sort_by,
        )
        return cur_sort_by

    def on_choose_lesson(self, meta: Meta) -> tuple:
        lesson_name = meta.name
        print(f"Choose lesson: {lesson_name}")
        self.state_lessons.save_cache(
            cur_lesson = lesson_name,
        )
        return lesson_name
