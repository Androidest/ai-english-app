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
FAV_LESSON = "Favourite"
PATH_FAV_SHEET = PATH_LESSONS / f"{FAV_LESSON}.xlsx"
PATH_FAV_META = PATH_LESSONS / f"{FAV_LESSON}.json"

class State_Lessons:
    def __init__(self):
        self.metas = gr.State(value={})
        self.cur_lesson = gr.State(value=None)
        self.sort_by = gr.State(value="")
        self.pending_uppdate_meta = gr.State(value=tuple())
    
    def load_to_outputs(self) -> tuple:
        metas: dict = {} # lessons meta
        if PATH_LESSONS.exists():
            for file_path in PATH_LESSONS.rglob(f"*.xlsx"):
                lesson_name = file_path.stem
                metas[lesson_name] = self.load_meta(lesson_name)

        cache = self.load_cache()
        cur_lesson = cache["cur_lesson"]
        cur_sort_by = cache["cur_sort_by"]

        if cur_lesson not in metas:
            cur_lesson = ""

        return metas, cur_lesson, cur_sort_by

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

        data = [
            { "EN":"hello", "CN":"你好", "ID": "halo" },
            { "EN":"Where the is a will, there is a way.", "CN":"有志者，事竟成", "ID": "Dimana ada kemauan, di situ ada jalan." },
            { "EN":"Did you eat?", "CN":"你吃了吗？", "ID": "Apakah kamu sudah makan?" },
        ]
        for i, v in enumerate(data):
            sheet[i] = v
        return sheet

    def save_favourite(
            self, 
            val: dict, 
            meta:dict, 
            idx:int
        ):

        """
        Saving favourite phrase can only be done from the origin lesson.

        val:
            The row of data from the target phrase is to be added to the Favourite sheet in dictionary form.
        meta & idx:
            The meta and idx from the currently loaded lesson (the origin)

        """

        val['ORIGIN'] = meta["name"]

        if not PATH_FAV_SHEET.exists():
            default_data = { key:[val] for key, val in val.items() }

            sheet = Sheet(PATH_FAV_SHEET, default_data=default_data, dtype=str)
            fav_meta = self.create_default_meta(FAV_LESSON, sheet)

            self.save_sheet(sheet)
            self.save_meta(fav_meta, override_all=True)

        else:
            sheet = Sheet(PATH_FAV_SHEET)
            fav_idx = self.find_phrase_idx(sheet, val["EN"])
            if fav_idx == -1:
                sheet.append(val)

                self.save_sheet(sheet)
                self.save_meta({ "name": FAV_LESSON, "total": len(sheet) }, override_all=False)

        self.set_favourite_phrase(meta, idx, True)
        self.make_brief_meta(meta)
        self.save_meta(meta)

    def delete_favourite(
            self, 
            en_key: str,
            meta:dict, 
            idx:int,
            is_origin:bool,
        ):
        """
        Remove the favourite phrase from:
            1. From the Favourite sheet 
            2. From the flags of the Favourite meta file. 
            3. From the flags of the origin meta file. 
        en_key:
            The target English phrase.
        meta & idx:
            Provide the meta and the idx either from the currently loaded origin or the Favourite lesson. 
        is_origin:
            The provided meta and idx is from the origin or from the Favourite lesson. 

        return:
            fav_sheet
        """

        origin_meta, fav_meta = None, None
        origin_idx, fav_idx = -1, -1
        fav_sheet = None
        pending_origin = None

        # deal it from the origin meta
        if is_origin:
            origin_meta = meta
            origin_idx = idx

            if PATH_FAV_SHEET.exists():
                fav_sheet = self.load_sheet(FAV_LESSON)
                fav_idx = self.find_phrase_idx(fav_sheet, en_key)
                if PATH_FAV_META.exists():
                    fav_meta = self.load_meta(FAV_LESSON)
        else:
            fav_meta = meta
            fav_idx = idx
            fav_sheet = self.load_sheet(FAV_LESSON)
            origin = fav_sheet[fav_idx, "ORIGIN"]
            
            if (PATH_LESSONS / f"{origin}.xlsx").exists():
                origin_sheet = self.load_sheet(origin)
                origin_idx = self.find_phrase_idx(origin_sheet, en_key)
                if (PATH_LESSONS / f"{origin}.json").exists():
                    origin_meta = self.load_meta(origin)

        # remove the favourite flag from the origin meta
        if origin_meta != None and origin_idx > -1:
            self.set_favourite_phrase(origin_meta, origin_idx, False)
            self.make_brief_meta(origin_meta)
            self.save_meta(origin_meta)
            pending_origin = origin_meta["name"]

        if fav_meta != None and fav_idx > -1:
            # delete it from the Favourite sheet
            fav_sheet.delete_by_index(fav_idx)
            fav_sheet.reset_index()
            self.save_sheet(fav_sheet)

            # remove the favourite flag from the favourite meta
            flags = {}
            for k, v in fav_meta["phrases_flag"].items():
                if int(k) < fav_idx:
                    flags[k] = v
                else:
                    flags[str(int(k)-1)] = v

            fav_meta["phrases_flag"] = flags
            self.make_brief_meta(fav_meta, len(fav_sheet))
            self.save_meta(fav_meta)

        return fav_sheet, pending_origin

    def find_phrase_idx(self, sheet: Sheet, en: str):
        mask = sheet.dataframe["EN"] == en
        positions = sheet.dataframe[mask].index.tolist()
        if len(positions) > 0:
            return positions[0]
        return -1

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

    def set_favourite_phrase(self, meta: dict, idx: int, is_favourite: bool):
        if is_favourite:
            meta["phrases_flag"][str(idx)] = meta["phrases_flag"].get(str(idx), 0) | IS_FAVORITE
        else:
            meta["phrases_flag"][str(idx)] = meta["phrases_flag"].get(str(idx), 0) & ~IS_FAVORITE
            if meta["phrases_flag"][str(idx)] == 0:
                del meta["phrases_flag"][str(idx)]
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