# Code design template for workflows

from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field
from typing import Literal, TypedDict
from langgraph.runtime import Runtime

from app.workflow._core_.runnable import ConstrainedOutputWithRetry 
from app.workflow._core_.llm_config import LLMConfig 
from app.workflow._core_.llm_runtime import LLMRuntime 
from app.workflow._core_.context import BasicWorkflowContext 

# ====================================================================
#region definition of a schema

# Example inside a schema file 'reporter.py' in 'app/workflow/schemas'

class Reporter(BaseModel):
    """Reporter info""" # output constraint prompts
    p_name: str = Field(description="人物名字") # output constraint prompts inside a field description
    p_age: int = Field(ge=1, le=300)
    loc: str

#endregion definition of a schema


# ====================================================================
#region definition of a state

# Example inside a state file 'reporter_extractor_state.py' in 'app/workflow/states'

class ReporterExtractorState(TypedDict):
    input: str # workflow input
    output: Reporter # workflow output

#endregion definition of a schema


# ====================================================================
#region definition of a node

# Example inside a node file 'extract.py' in 'app/workflow/nodes'

# Nodes' sys prompts are defined along with the node definition. The business instruction template for the node goes here.
SYS_PROMPT_TEMPLATE = 'Extract information from the given sentence:\n{input}'

def extract(
    state: ReporterExtractorState, 
    runtime: Runtime[BasicWorkflowContext]
) -> ReporterExtractorState:

    """Node: Extract a reporter information from the input"""

    # get all the required inputs and data for this node from the state
    input = state['input']

    # The output validation function goes here. 
    # Tell the llm to try to correct its output by rasing an error when the validation fails.
    def verify_cb(o: Reporter):
        # Sometimes, we may also need the input to assist with validation (not in this example)
        if o.p_age <= 0:
            raise Exception("Age cannot be equals or smaller than 0!")
        if o.p_name == "":
            raise Exception("Name should not be empty. Extract again.")

    # get the model from the runtime cache
    llm = runtime.context.llm_runtime.get_model(
        temperature=1, # Sometimes need different temperatures for different situations.
    )

    # Use ConstrainedOutputWithRetry when situations require structured or semi-structured outputs.
    llm = ConstrainedOutputWithRetry(
        llm=llm,
        out_schema=Reporter,
        verify_cb=verify_cb,
        max_retries=2,
        keep_all_errors=True,
    )

    # merge the inputs into the sys prompts
    sys_propmt = SYS_PROMPT_TEMPLATE.format(input=input)
    
    # Invoke an llm or a specially modified llm to process the input
    o = llm.invoke(
        input=sys_propmt,
        context=runtime.context,
    )

    # update the state
    return ReporterExtractorState(
        output=o
    )

#endregion definition of a node


# ====================================================================
#region definition of a graph

# Example inside a graph file 'reporter_extractor.py' in 'app/workflow/graphs'

class ReporterExtractor:
    """ A workflow that can extract a reporter information from a given sentence."""

    def __init__(self):
        self.graph = self._build_graph()

    def _build_graph(self):

        """Reproter info extractor workflow"""

        builder = StateGraph(
            state_schema=ReporterExtractorState, 
            context_schema=BasicWorkflowContext
        )

        # add nodes
        builder.add_node("extract", extract)

        # add edges
        builder.add_edge(START, "extract")
        builder.add_edge("extract", END)

        # build the workflow
        return builder.compile()

    def invoke(self, 
        input: str,
        llm_config: LLMConfig,
        user_id: str,
    ) -> Reporter:

        """
        Invoke extraction
        args:
            input: The target sentence.
            llm_config: The expected LLM that is supposed be used by the workflow.
        """

        initial_state = ReporterExtractorState(
            input=input,
        )
        
        context = BasicWorkflowContext(
            user_id=user_id,
            llm_runtime=LLMRuntime(config=llm_config),
        )

        final_state : ReporterExtractorState = self.graph.invoke(
            input=initial_state, 
            context=context
        )

        return final_state['output']
        

#endregion definition of a graph


# ====================================================================
#region definition of a workflow testing

# Example inside a workflow testing file 'test_reporter_extractor.py' in the 'app/workflow/tests'

# Get the LLM configs from the test env
from app.utils.config import config_dict, set_config
set_config('test')
from app.utils.config import config

input='A 20-years-old man called John reported suspicious activity in the parking station.'

llm_config=LLMConfig(
    alias="test",
    model_provider=config.TEST_MODEL_PROVIDER,
    model=config.TEST_MODEL,
    base_url=config.TEST_BASE_URL,
    api_key=config.TEST_API_KEY,
)

workflow = ReporterExtractor() 
reporter = workflow.invoke(
    input=input, 
    llm_config=llm_config, 
    user_id="xxx"
)

print('Info:', input)
print('Reporter:', reporter)

#endregion test workflow
