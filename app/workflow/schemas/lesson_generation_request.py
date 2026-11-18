from pydantic import BaseModel, Field

from app.utils.types import CEFRLevel, Language

SOURCE_MAX_LENGTH_TOLERANCE = 25

class LessonGenerationRequest(BaseModel):
    """Public input of the multilingual lesson generation workflow."""

    source_language: Language = Field(default=Language.__args__[0])
    source_max_len: int = Field(ge=SOURCE_MAX_LENGTH_TOLERANCE+10, le=300, default=100)
    topic: str = Field(min_length=1)
    difficulty: CEFRLevel  = Field(default=CEFRLevel.__args__[0])
    target_count: int = Field(ge=1, le=500, default=10)

    translation_languages :list[Language] = Field(min_length=1)
    
    batch_size: int = Field(ge=1, le=50, default=5)
    max_concurrency: int = Field(ge=1, le=50, default=20)

    def get_src_max_len_for_prompt(self):

        """
        Get the calibrated source maximum length:
            LLMs have difficulties controlling sentence generation length.
            If we don't take tolerance into account, most of the generation will exceed the expected max length. 
            And the workflow will still fail even with many retries. 
            We should use a relatively smaller max length for the prompt 
            and use the actual max length for the validation to improve the success rate.
        """

        prompt_src_max_len = self.source_max_len
        if self.source_max_len > SOURCE_MAX_LENGTH_TOLERANCE:
            prompt_src_max_len = self.source_max_len - SOURCE_MAX_LENGTH_TOLERANCE

        return prompt_src_max_len
