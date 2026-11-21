import gradio as gr
from app.ui.dialogs.confirm_dialog import ConfirmDialog
from app.ui.models.meta import Meta
from app.ui.states.state_llm import State_LLM
from app.ui.states.state_lesson import State_Lesson
from app.ui.components.tab_lesson_list import Tab_Lesson_List
from app.ui.components.tab_lesson_chosen import Tab_Lesson_Chosen
from app.ui.dialogs.gen_lesson_dialog import GenLessonDialog
from app.ui.dialogs.lesson_gen_info_dialog import LessonGenInfoDialog

class Tab_Lesson:

    def __init__(
            self, 
            state_lesson: State_Lesson, 
            state_llm: State_LLM, 
            confirm_dialog: ConfirmDialog, 
            gen_lesson_dialog: GenLessonDialog,
            lesson_gen_info_dialog: LessonGenInfoDialog,
        ):

        with gr.Tab("Lessons"):

            @gr.render(inputs=[state_lesson.metas, state_lesson.cur_lesson])
            def render_tab(metas: Meta, cur_lesson: str):   
                if cur_lesson == None:
                    return

                if cur_lesson == "":
                    Tab_Lesson_List(
                        state_lesson, 
                        gen_lesson_dialog
                    )
                else:
                    Tab_Lesson_Chosen(
                        state_lesson, 
                        state_llm, 
                        confirm_dialog, 
                        metas, 
                        cur_lesson,
                        lesson_gen_info_dialog,
                    )
