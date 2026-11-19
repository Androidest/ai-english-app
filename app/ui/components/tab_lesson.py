import gradio as gr
from app.ui.dialogs.confirm_dialog import ConfirmDialog
from app.ui.models.meta import Meta
from app.ui.states.state_llms import State_LLMs
from app.ui.states.state_lessons import State_Lessons
from app.ui.components.tab_lesson_list import Tab_Lesson_List
from app.ui.components.tab_lesson_chosen import Tab_Lesson_Chosen
from app.ui.dialogs.gen_lesson_dialog import GenLessonDialog
from app.ui.dialogs.lesson_gen_info_dialog import LessonGenInfoDialog

class Tab_Lesson:

    def __init__(
            self, 
            state_lessons: State_Lessons, 
            state_llms: State_LLMs, 
            confirm_dialog: ConfirmDialog, 
            gen_lesson_dialog: GenLessonDialog,
            lesson_gen_info_dialog: LessonGenInfoDialog,
        ):

        with gr.Tab("Lessons"):

            @gr.render(inputs=[state_lessons.metas, state_lessons.cur_lesson])
            def render_tab(metas: Meta, cur_lesson: str):   
                if cur_lesson == None:
                    return

                if cur_lesson == "":
                    Tab_Lesson_List(
                        state_lessons, 
                        gen_lesson_dialog
                    )
                else:
                    Tab_Lesson_Chosen(
                        state_lessons, 
                        state_llms, 
                        confirm_dialog, 
                        metas, 
                        cur_lesson,
                        lesson_gen_info_dialog,
                    )
