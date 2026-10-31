from __future__ import annotations

from typing import Any, Callable, Type, Literal

from pydantic import BaseModel
from langchain_core.language_models import LanguageModelLike
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.runnables import Runnable

FIX_ERROR_TITLE = "Validation error:"

FIX_ERROR_TEMPLATE = FIX_ERROR_TITLE + """
{error}

The previous output failed validation.
Please fix it according to the validation error.

Important:
- Preserve all valid information from the previous output.
- Only modify the parts necessary to fix the error.
- Return only the corrected structured output.
"""


class ConstrainedOutputWithRetry(Runnable):
    """
    LLM with constrained output, validation and llm self-repairing.
    
    args:
        constraint_prompt(optional):
            For custom semi-structured output, e.g., True or False, 0 or 1, markdown, etc.
        out_schema(optional):
            For json structured output.
        verify_cb:
            The validation callback. Pass the error message to the LLM by raising an error.
        keep_all_errors:
            'True' to keep all the error outputs and corrections in the chat history. 
            'False' to keep only the last output.
        method:

    """

    def __init__(
        self,
        llm: LanguageModelLike,
        out_schema: Type[BaseModel] = None,
        verify_cb: Callable[[BaseModel], None] | None = None,
        keep_all_errors: bool = False,
        max_retries: int = 3,
        method:Literal["json_schema", "json_mode", "function_calling"] ="json_schema",
    ):
        self.llm = llm
        self.out_schema = out_schema
        self.max_retries = max_retries
        self.verify_cb = verify_cb
        self.keep_all_errors = keep_all_errors

        if out_schema:
            # structures output
            self.llm_structured = llm.with_structured_output(
                schema=out_schema,
                method=method,
                include_raw=True,
            )
        else:
            # semi-structure output.  
            self.llm_structured = None

    async def ainvoke(
        self,
        input: Any,
        config=None,
        **kwargs,
    ):
        messages = self._to_messages(input)
        output = None

        for attempt in range(self.max_retries + 1):

            try:
                if self.llm_structured:
                    output = await self.llm_structured.ainvoke(
                        messages,
                        config=config,
                        **kwargs,
                    )

                    # Schema / JSON parsing error
                    if output["parsing_error"] is not None:
                        raise output["parsing_error"]

                    out = output["parsed"]
                else:
                    output = await self.llm.ainvoke(
                        messages,
                        config=config,
                        **kwargs,
                    )
                    out = output.content

                # Business validation
                if self.verify_cb is not None:
                    self.verify_cb(out) # if validation fails, the callback will raise an error

                return out

            except Exception as e:

                if not self.keep_all_errors and messages[-1].content.startswith(FIX_ERROR_TITLE):
                    messages.pop()
                    messages.pop()
                    # remove the last error from the history

                # save the last output into the history
                if output is not None:
                    if self.llm_structured:
                        messages.append(output["raw"])
                    else:
                        messages.append(output)

                    # Report the validation error
                    messages.append(
                        HumanMessage(
                            content=FIX_ERROR_TEMPLATE.format(error=str(e))
                        )
                    )
                else:
                    raise Exception("llm output is of type function and is not JSON serializable")

        # reached max retries
        error = f"=======================================================================\n"
        error += f"[ConstrainedOutputWithRetry] Has reached max retries: {self.max_retries}\n"

        for m in messages:
            error += '\n\n'
            error += "---------------------------------------------------------------------\n"
            error += f'{m.type}:\n'
            if m.type == 'ai':
                error += str(m)
            else:
                error += str(m.content)
        raise Exception(error)


    def invoke(
        self,
        input: Any,
        config=None,
        **kwargs,
    ):
        messages = self._to_messages(input)
        output = None

        for attempt in range(self.max_retries + 1):

            try:
                if self.llm_structured:
                    output = self.llm_structured.invoke(
                        messages,
                        config=config,
                        **kwargs,
                    )

                    # Schema / JSON parsing error
                    if output["parsing_error"] is not None:
                        raise output["parsing_error"]

                    out = output["parsed"]
                else:
                    output = self.llm.invoke(
                        messages,
                        config=config,
                        **kwargs,
                    )
                    out = output.content

                # Business validation
                if self.verify_cb is not None:
                    self.verify_cb(out) # if validation fails, the callback will raise an error

                return out

            except Exception as e:

                if not self.keep_all_errors and messages[-1].content.startswith(FIX_ERROR_TITLE):
                    messages.pop()
                    messages.pop()
                    # remove the last error from the history

                # save the last output into the history
                if output is not None:
                    if self.llm_structured:
                        messages.append(output["raw"])
                    else:
                        messages.append(output)

                    # Report the validation error
                    messages.append(
                        HumanMessage(
                            content=FIX_ERROR_TEMPLATE.format(error=str(e))
                        )
                    )
                else:
                    raise Exception("llm output is of type function and is not JSON serializable")

        # reached max retries
        error = f"=======================================================================\n"
        error += f"[ConstrainedOutputWithRetry] Has reached max retries: {self.max_retries}\n"

        for m in messages:
            error += '\n\n'
            error += "---------------------------------------------------------------------\n"
            error += f'{m.type}:\n'
            if m.type == 'ai':
                error += str(m)
            else:
                error += str(m.content)
        raise Exception(error)

    @staticmethod
    def _to_messages(input: Any) -> list[BaseMessage]:

        if isinstance(input, str):
            return [
                SystemMessage(content=input)
            ]

        if isinstance(input, BaseMessage):
            return [input]

        if isinstance(input, list):
            return input

        # PromptValue
        if hasattr(input, "to_messages"):
            return input.to_messages()

        raise TypeError(
            f"Unsupported input type: {type(input)}"
        )