from pydantic import BaseModel, Field, model_validator

from app.workflow.schemas.lesson_generation_request import LessonGenerationRequest
from app.utils.types import LANG_OPTIONS, Language, CEFRLevel

DEFAULT_LANG_OPTION = LANG_OPTIONS.__args__[0]

class LessonGenParams(LessonGenerationRequest):
    translation_languages :list[Language] = Field(default_factory=list, exclude=True) # overwrite parent field
    display_language_1: LANG_OPTIONS = DEFAULT_LANG_OPTION
    display_language_2: LANG_OPTIONS = DEFAULT_LANG_OPTION

    @model_validator(mode="before")
    @classmethod
    def _derive_translation_languages(cls, data):
        if not isinstance(data, dict):
            return data
    
        data = dict(data)
        source_language = data.get("source_language", "")
        langs = []
        for key in ("display_language_1", "display_language_2"):
            lang = data.get(key, DEFAULT_LANG_OPTION)
            if lang in Language.__args__ and lang not in langs and lang != source_language:
                langs.append(lang)

        data["translation_languages"] = langs
        return data

    def to_request(self) -> LessonGenerationRequest:
        model = self.model_dump(
            exclude=["display_language_1", "display_language_2"]
        )
        model["translation_languages"] = self.translation_languages.copy()
        return LessonGenerationRequest(**model)

    def validate(self) -> tuple[bool, str]:
        errors = []

        if self.source_language not in Language.__args__:
            errors.append("`Source language` is required!")

        if self.source_max_len <= 0 or self.source_max_len == None:
            errors.append("`Max sentence length` should be a number bigger than `0`.")

        if self.topic == "":
            errors.append("`Topic` is required!")

        if self.difficulty not in CEFRLevel.__args__:
            errors.append("`Difficulty` is required!")

        if self.target_count <= 0 or self.target_count == None:
            errors.append("`Pages` should be a number bigger than `0`.")

        if self.batch_size <= 0 or self.batch_size == None:
            errors.append("`Batch size` should be a number bigger than `0`.")

        if self.max_concurrency <= 0 or self.max_concurrency == None:
            errors.append("`Max concurrency` should be a number bigger than `0`.")

        if not self.translation_languages:
            errors.append("A least one `display language`<br>different from the `source language` is required.")

        all = [self.source_language]
        if self.display_language_1 != DEFAULT_LANG_OPTION:
            all.append(self.display_language_1)
        if self.display_language_2 != DEFAULT_LANG_OPTION:
            all.append(self.display_language_2)

        if len(set(all)) != len(all):
            errors.append("Source language and all the display languages must be distinct.<br>No duplicates are allowed.")

        return len(errors) == 0, errors 

    
LESSON_GEN_PARAMS_ORDER = [ 
    field 
    for field in LessonGenParams.model_fields.keys()
    if field != "translation_languages"
]

