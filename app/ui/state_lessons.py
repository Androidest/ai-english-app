import gradio as gr
from app.utils.paths import PATH_LESSONS
from app.utils.sheet import Sheet
import json

IS_FAVORITE = 0b01
IS_PASSED = 0b10

SORT_LATEST = "latest"
SORT_OLDEST = "oldest"
SORT_ALPHA_A_Z = "A → Z"
SORT_ALPHA_Z_A = "Z → A"

PATH_CACHE = PATH_LESSONS / "cache.json"

class State_Lessons:
    def __init__(self):
        self.metas = gr.State(value={})
        self.cur_lesson = gr.State(value=None)
        self.sort_by = gr.State(value="")
    
    def load_to_outputs(self) -> tuple:
        lessons: dict = {} # lessons meta
        if PATH_LESSONS.exists():
            for file_path in PATH_LESSONS.rglob(f"*.xlsx"):
                lesson_name = file_path.stem
                lessons[lesson_name] = self.load_meta(lesson_name)

        cache = self.load_cache()
        cur_lesson = cache["cur_lesson"]
        cur_sort_by = cache["cur_sort_by"]

        return lessons, cur_lesson, cur_sort_by

    def outputs(self):
        return [self.metas, self.cur_lesson, self.sort_by]

    # region Cache Management

    def create_default_cache(self) -> dict:
        return {
            "cur_lesson": "",
            "cur_sort_by": SORT_LATEST,
        }

    def load_cache(self) -> dict:
        if PATH_CACHE.exists():
            with open(PATH_CACHE, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            cache = self.create_default_cache()
            self.save_cache(cache, override_all=True)
            return cache
        
    def save_cache(self, cache: dict, override_all: bool = False):
        if not PATH_LESSONS.exists():
            PATH_LESSONS.mkdir(parents=True, exist_ok=True)

        # Update existing cache
        if PATH_CACHE.exists() and not override_all:
            with open(PATH_CACHE, "r", encoding="utf-8") as f:
                old_cache = json.load(f)
                cache = { **old_cache, **cache }

        # Save cache to file
        with open(PATH_CACHE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=4)

        return cache

    # endregion Cache Management

    # region sheet Management Functions

    def generate_sheet(self, lesson_name: str, pages, prompts: str, llm_config: dict):
        # TODO
        sheet = Sheet(PATH_LESSONS / f"{lesson_name}.xlsx", default_data={'EN':[], 'CN':[], 'ID':[]}, dtype=str)
        for i in range(0, pages):
            sheet[i, "EN"] = "hello"
            sheet[i, "CN"] = "你好"
            sheet[i, "ID"] = "halo"
        return sheet

    def save_sheet(self, sheet: Sheet):
        if not PATH_LESSONS.exists():
            PATH_LESSONS.mkdir(parents=True, exist_ok=True)

        sheet.save()

    def load_sheet(self, lesson_name: str) -> Sheet:
        path = PATH_LESSONS / f"{lesson_name}.xlsx"
        if not path.exists():
            raise ValueError(f"Lesson {lesson_name} does not exist")

        sheet = Sheet(path)
        return sheet

    def delete_sheet(self, lesson_name: str):
        path = PATH_LESSONS / f"{lesson_name}.xlsx"
        if path.exists():
            path.unlink()

    # endregion Lesson Management Functions

    # region Meta Management Functions

    def create_default_meta(self, lesson_name: str, sheet: Sheet) -> dict:
        meta = {
            "name": lesson_name,
            "time_created": sheet.time_created,
            "progress_idx": 0, 
            "phrases_flag": {},
        }
        meta = self.make_brief_meta(meta, len(sheet))
        return meta

    def save_meta(self, meta: dict, override_all: bool = False):
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

    def load_meta(self, lesson_name: str) -> dict:
        meta_path = PATH_LESSONS / f"{lesson_name}.json"
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            sheet = self.load_sheet(lesson_name)
            meta = self.create_default_meta(lesson_name, sheet)
            self.save_meta(meta, override_all=True)
            return meta

    def delete_meta(self, lesson_name: str):
        path = PATH_LESSONS / f"{lesson_name}.json"
        if path.exists():
            path.unlink()

    def make_brief_meta(self, meta: dict, total: int = None) -> dict:
        if total is not None:
            meta["total"] = total

        correct_count = 0
        favourite_count = 0

        for idx in meta["phrases_flag"].keys():
            if self.is_phrase_passed(meta, idx):
                correct_count += 1
            if self.is_phrase_favourite(meta, idx):
                favourite_count += 1

        meta["correct_count"] = correct_count
        meta["favourite_count"] = favourite_count

        return meta

    def update_progress(self, meta: dict, idx: int):
        if idx < 0:
            idx = 0
        elif idx >= meta["total"]:
            idx = meta["total"] - 1
        meta["progress_idx"] = idx
        return meta

    def is_phrase_passed(self, meta: dict, idx: int) -> bool:
        return meta["phrases_flag"].get(str(idx), 0) & IS_PASSED == IS_PASSED

    def is_phrase_favourite(self, meta: dict, idx: int) -> bool:
        return meta["phrases_flag"].get(str(idx), 0) & IS_FAVORITE == IS_FAVORITE

    def toggle_phrase_favorite(self, meta: dict, idx: int):
        meta["phrases_flag"][str(idx)] = meta["phrases_flag"].get(str(idx), 0) ^ IS_FAVORITE
        return meta

    def set_pass_phrase(self, meta: dict, idx: int, is_correct: bool):
        if is_correct:
            meta["phrases_flag"][str(idx)] = meta["phrases_flag"].get(str(idx), 0) | IS_PASSED
        else:
            meta["phrases_flag"][str(idx)] = meta["phrases_flag"].get(str(idx), 0) & ~IS_PASSED
        return meta

    def reset_meta(self, meta: dict):
        meta["phrases_flag"] = {
            idx: flag & ~IS_PASSED
            for idx, flag in meta["phrases_flag"].items() if flag != IS_PASSED
        }
        meta["progress_idx"] = 0 # back to the first phrase
        meta = self.make_brief_meta(meta)
        return meta
    
    # endregion Meta Management Functions

     # region Misc Functions
        
    def sort_lessons(self, lessons: dict, sort_by: str) -> list[(str, dict)]:
        if sort_by == SORT_LATEST:
            return sorted(lessons.items(), key=lambda item: item[1]["time_created"], reverse=True)
        elif sort_by == SORT_OLDEST:
            return sorted(lessons.items(), key=lambda item: item[1]["time_created"])
        elif sort_by == SORT_ALPHA_A_Z:
            return sorted(lessons.items(), key=lambda item: item[0])
        elif sort_by == SORT_ALPHA_Z_A:
            return sorted(lessons.items(), key=lambda item: item[0], reverse=True)
        return []
    
    def filter_lessons(self, lessons: dict, search: str) -> dict:
        if search == "":
            return lessons
        else:
            return { k: v for k, v in lessons.items() if search in k or search in v["name"] }

    # endregion Misc Functions