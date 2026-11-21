from typing import TypedDict, Unpack
import gradio as gr
import json
import random

from app.ui.models.cache import Cache, CacheUpdate
from app.ui.models.meta import Meta, MetaUpdate
from app.ui.models.lesson_gen_params import LessonGenParams
from app.utils.paths import PATH_LESSONS
from app.utils.sheet import Sheet
from app.utils.types import Language, SORTING_OPTIONS

IS_FAVORITE = 0b01
IS_PASSED = 0b10

PATH_CACHE = PATH_LESSONS / "cache.json"
FAV_LESSON = "Favourite"
PATH_FAV_SHEET = PATH_LESSONS / f"{FAV_LESSON}.xlsx"
PATH_FAV_META = PATH_LESSONS / f"{FAV_LESSON}.json"


class State_Lessons:
    def __init__(self):
        self.metas: dict[str, Meta] = gr.State(value={})
        self.cur_lesson = gr.State(value=None)
        self.sort_by = gr.State(value="")
        self.cache = gr.State(value=None)
        self.pending_uppdate_meta = gr.State(value=tuple())
    
    def load_to_outputs(self) -> tuple:
        metas: dict[str, Meta] = {} # lessons meta
        if PATH_LESSONS.exists():
            for file_path in PATH_LESSONS.rglob(f"*.xlsx"):
                lesson_name = file_path.stem
                metas[lesson_name] = self.load_meta(lesson_name)

        cache = self.load_cache()
        cur_lesson = cache.cur_lesson
        cur_sort_by = cache.cur_sort_by

        if cur_lesson not in metas:
            cur_lesson = ""

        return (
            metas, 
            cur_lesson, 
            cur_sort_by,
            cache,
        )

    def outputs(self):
        return [
            self.metas, 
            self.cur_lesson, 
            self.sort_by,
            self.cache
        ]

    # region Cache Management

    def load_cache(self) -> Cache:
        if PATH_CACHE.exists():
            with open(PATH_CACHE, "r", encoding="utf-8") as f:
                return Cache.model_validate(json.load(f))
        else:
            cache = self.save_cache(reset=True)
            return cache
        
    def save_cache(
        self, 
        cache: Cache = None,
        reset: bool = False,
        **updates: Unpack[CacheUpdate]
    ) -> Cache:
        
        if not PATH_LESSONS.exists():
            PATH_LESSONS.mkdir(parents=True, exist_ok=True)

        cache_dict: dict = {}

        # Prepaire full update
        if cache:
            cache_dict = cache.model_dump()

        # Prepaire partial update. Overwrite the existing older version if possible
        elif PATH_CACHE.exists() and updates:
            with open(PATH_CACHE, "r", encoding="utf-8") as f:
                cache_dict = json.load(f)

        # `updates` has higher priority
        if updates:
            cache_dict.update(updates)

        if not reset and not cache_dict:
            raise ValueError("No values provided. To save the DEFAULT version, use `reset=True`.")

        # ensure full meta
        cache = Cache.model_validate(cache_dict)

        # Save cache to file
        with open(PATH_CACHE, "w", encoding="utf-8") as f:
            json.dump(cache.model_dump(), f, ensure_ascii=False, indent=4)

        return cache

    # endregion Cache Management

    # region sheet Management Functions

    def build_sheet(
        self, 
        lesson_name: str, 
        data: list[dict[str, str]],
        display_languages_order: list[Language],
    ) -> Sheet:
        lang_key_map = { display_languages_order[0]: "DIS_1" }
        if len(display_languages_order) > 1:
            lang_key_map[display_languages_order[1]] = "DIS_2"
            
        sheet = Sheet(PATH_LESSONS / f"{lesson_name}.xlsx", default_data={'SRC':[], 'DIS_1':[], 'DIS_2':[]}, dtype=str)

        for i, item in enumerate(data):
            sheet[i] = {
                lang_key_map.get(lang, "SRC"): sentence
                for lang, sentence in item.items()
            }

        return sheet

    def save_favourite(
        self, 
        val: dict, 
        meta: Meta, 
        idx: int
    ):

        """
        Saving favourite phrase can only be done from the origin lesson.

        val:
            The row of data from the target phrase is to be added to the Favourite sheet in dictionary form.
        meta & idx:
            The meta and idx from the currently loaded lesson (the origin)

        """

        val['ORIGIN'] = meta.name

        if not PATH_FAV_SHEET.exists():
            default_data = { key:[val] for key, val in val.items() }

            sheet = Sheet(PATH_FAV_SHEET, default_data=default_data, dtype=str)
            fav_meta = self.create_default_meta(FAV_LESSON, sheet)

            self.save_sheet(sheet)
            self.save_meta(fav_meta)

        else:
            sheet = Sheet(PATH_FAV_SHEET)
            fav_idx = self.find_phrase_idx(sheet, val["SRC"])
            if fav_idx == -1:
                sheet.append(val)

                fav_meta = self.load_meta(FAV_LESSON)
                if fav_meta.progress_idx < 0:
                    fav_meta["progress_idx"] = 0
                fav_meta.total = len(sheet)

                self.save_sheet(sheet)
                self.save_meta(fav_meta)

        self.set_favourite_phrase(meta, idx, True)
        self.make_brief_meta(meta)
        self.save_meta(meta)

    def delete_favourite(
        self, 
        en_key: str,
        meta:Meta, 
        idx:int,
        is_origin:bool,
    ) -> tuple[Sheet, str]:
        
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

        origin_meta: Meta = None
        fav_meta: Meta = None
        origin_idx, fav_idx = -1, -1
        fav_sheet: Sheet = None
        pending_origin: str = None

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
            pending_origin = origin_meta.name

        if fav_meta != None and fav_idx > -1:
            # delete it from the Favourite sheet
            fav_sheet.delete_by_index(fav_idx)
            fav_sheet.reset_index()
            self.save_sheet(fav_sheet)

            # remove the favourite flag from the favourite meta
            flags = {}
            for k, v in fav_meta.phrases_flag.items():
                if int(k) < fav_idx:
                    flags[k] = v
                elif int(k) > fav_idx:
                    flags[str(int(k)-1)] = v

            fav_meta.phrases_flag = flags
            fav_meta = self.make_brief_meta(fav_meta, len(fav_sheet))
            fav_meta = self.save_meta(fav_meta)

        return fav_sheet, pending_origin

    def find_phrase_idx(
        self, 
        sheet: Sheet, 
        src: str
    ) -> int:
        
        mask = sheet.dataframe["SRC"] == src
        positions = sheet.dataframe[mask].index.tolist()
        if len(positions) > 0:
            return positions[0]
        return -1

    def save_sheet(
        self, 
        sheet: Sheet
    ):
        if not PATH_LESSONS.exists():
            PATH_LESSONS.mkdir(parents=True, exist_ok=True)

        sheet.save()

    def load_sheet(
        self, 
        lesson_name: str
    ) -> Sheet:
        path = PATH_LESSONS / f"{lesson_name}.xlsx"
        if not path.exists():
            raise ValueError(f"Lesson {lesson_name} does not exist")

        sheet = Sheet(path)
        return sheet

    def delete_sheet(
        self, 
        lesson_name: str
    ):
        path = PATH_LESSONS / f"{lesson_name}.xlsx"
        if path.exists():
            path.unlink()

    # endregion Lesson Management Functions

    # region Meta Management Functions

    def create_default_meta(
        self, 
        lesson_name: str, 
        sheet: Sheet,
        gen_params: LessonGenParams = None,
    ) -> Meta:
        
        meta = Meta(
            name = lesson_name,
            time_created = sheet.get_time_created(),
            gen_params = gen_params if gen_params else LessonGenParams(),
        )
        meta = self.make_brief_meta(meta, len(sheet))
        return meta

    def save_meta(
        self, 
        meta: Meta = None,
        **updates: Unpack[MetaUpdate]
    ) -> Meta:
        
        if not PATH_LESSONS.exists():
            PATH_LESSONS.mkdir(parents=True, exist_ok=True)

        name = None
        if meta:
            name = meta.name
        elif "name" in updates:
             name = updates["name"]
             
        if not name:
            raise ValueError(f"No name provided. Not found in neither `meta` or `updates` parameters.")
        
        if not (PATH_LESSONS / f"{name}.xlsx").exists():
            raise ValueError(f"Lesson {meta.name} excel file does not exist")

        # may be a partial update dict
        meta_dict: dict = {}

        # Prepaire full update
        if meta:
            meta_dict = meta.model_dump()

        # Update existing meta
        meta_path = PATH_LESSONS / f"{meta.name}.json"
        if meta_path.exists() and updates:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta_dict = json.load(f)

        if updates:
            meta_dict.update(updates)

        # ensure full meta
        meta = Meta.model_validate(meta_dict)

        # Save meta to file
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta.model_dump(), f, ensure_ascii=False, indent=4)

        return meta

    def load_meta(
        self, 
        lesson_name: str
    ) -> Meta:
        
        meta_path = PATH_LESSONS / f"{lesson_name}.json"
        
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                return Meta.model_validate(json.load(f))
        else:
            sheet = self.load_sheet(lesson_name)
            meta = self.create_default_meta(lesson_name, sheet)
            self.save_meta(meta)
            return meta

    def delete_meta(
        self, 
        lesson_name: str
    ):
        path = PATH_LESSONS / f"{lesson_name}.json"
        if path.exists():
            path.unlink()

    def make_brief_meta(
        self, 
        meta: Meta, 
        total: int = None
    ) -> Meta:
        
        if total is not None:
            meta.total = total
            self.update_progress(meta, meta.progress_idx)

        correct_count = 0
        favourite_count = 0

        for idx in meta.phrases_flag.keys():
            if self.is_phrase_passed(meta, idx):
                correct_count += 1
            if self.is_phrase_favourite(meta, idx):
                favourite_count += 1

        meta.correct_count = correct_count
        meta.favourite_count = favourite_count

        return meta

    def update_progress(
        self, 
        meta: Meta, 
        idx: int
    ) -> Meta:
        
        if idx >= meta.total:
            idx = meta.total - 1
        if idx < 0:
            idx = 0
        meta.progress_idx = idx
        return meta

    def is_phrase_passed(
        self, 
        meta: Meta, 
        idx: int
    ) -> bool:
        return meta.phrases_flag.get(str(idx), 0) & IS_PASSED == IS_PASSED

    def is_phrase_favourite(
        self, 
        meta: Meta, 
        idx: int
    ) -> bool:
        return meta.phrases_flag.get(str(idx), 0) & IS_FAVORITE == IS_FAVORITE

    def toggle_phrase_favorite(
        self, 
        meta: Meta, 
        idx: int
    ) -> Meta:
        meta.phrases_flag[str(idx)] = meta.phrases_flag.get(str(idx), 0) ^ IS_FAVORITE
        return meta

    def set_favourite_phrase(
        self, 
        meta: Meta, 
        idx: int, 
        is_favourite: bool
    ) -> Meta:
        
        if is_favourite:
            meta.phrases_flag[str(idx)] = meta.phrases_flag.get(str(idx), 0) | IS_FAVORITE
        else:
            meta.phrases_flag[str(idx)] = meta.phrases_flag.get(str(idx), 0) & ~IS_FAVORITE
            if meta.phrases_flag[str(idx)] == 0:
                del meta.phrases_flag[str(idx)]
        return meta
    
    def set_pass_phrase(
        self, 
        meta: Meta, 
        idx: int, 
        is_correct: bool
    ) -> Meta:
        
        if is_correct:
            meta.phrases_flag[str(idx)] = meta.phrases_flag.get(str(idx), 0) | IS_PASSED
        else:
            meta.phrases_flag[str(idx)] = meta.phrases_flag.get(str(idx), 0) & ~IS_PASSED
        return meta

    def reset_meta(
        self, 
        meta: Meta
    ) -> Meta:
        
        meta.phrases_flag = {
            idx: flag & ~IS_PASSED
            for idx, flag in meta.phrases_flag.items() if flag != IS_PASSED
        }
        meta.progress_idx = 0 # back to the first phrase
        meta = self.make_brief_meta(meta)
        return meta
    
    # endregion Meta Management Functions

     # region Misc Functions
        
    def sort_lessons(
        self, 
        lessons: dict[str, Meta], 
        sort_by: SORTING_OPTIONS
    ) -> list[Meta]:
        
        if sort_by == "latest":
            return sorted(lessons.values(), key=lambda i: i.time_created, reverse=True)
        elif sort_by == "oldest":
            return sorted(lessons.values(), key=lambda i: i.time_created)
        elif sort_by == "A → Z":
            return sorted(lessons.values(), key=lambda i: i.name)
        elif sort_by == "Z → A":
            return sorted(lessons.values(), key=lambda i: i.name, reverse=True)
        return lessons.values()
    
    def filter_lessons(
        self, 
        lessons: dict[str, Meta], 
        search: str,
    ) -> dict[str, Meta]:
        
        if search == "":
            return lessons
        else:
            return { 
                k: v 
                for k, v in lessons.items() 
                if search in k or search in v.name
            }

    def reorganize_lessons(
        self,
        lessons: dict[str, Meta],
        sort_by: str,
        search: SORTING_OPTIONS,
    ) ->  list[Meta]:
        
        # search lessons
        filtered_lessons = self.filter_lessons(lessons, search)

        # cache the Favourite lesson
        fav_meta = None
        if FAV_LESSON in filtered_lessons:
            fav_meta = filtered_lessons[FAV_LESSON]
            filtered_lessons = { k:v for k,v in filtered_lessons.items() if k != FAV_LESSON }

        # sort lessons
        sorted_lessons = self.sort_lessons(filtered_lessons, sort_by)

        # put the Favourite at the start of the list
        if fav_meta != None:
            sorted_lessons.insert(0, fav_meta)

        return sorted_lessons

    def random_mask_word(
        self, 
        word: str, 
        mask_ratio: float = 0.3, 
        seed: int = None,
    ):
        """
        Randomly mask a word by replacing a fraction of its letters with spaces, 
        where the fraction is controlled by the `ratio` parameter
        """
        if seed is not None:
            random.seed(seed)
        
        chars = list(word)
        n = len(chars)
        mask_count = int(n * mask_ratio)  
        
        indices = random.sample(range(n), mask_count)
        for i in indices:
            chars[i] = '•'
        
        return ''.join(chars)

    
    # endregion Misc Functions