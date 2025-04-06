import json
import uuid
from typing import TypedDict, Annotated

from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END, add_messages
from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel

from logger_setup import logger
from prompt import BUDDY_PROMPT, ANALYZER_PROMPT, GUARDIAN_PROMPT
from tool import modify_characteristics, notify_dependents
from util import characteristics_reducer, validate_email

load_dotenv()

_checkpointer = MemorySaver()


class State(TypedDict):
    messages: Annotated[list, add_messages]
    characteristics: Annotated[list[str], characteristics_reducer]


class Character(BaseModel):
    characteristics: list[str]


class Agent:
    _llm = ChatOpenAI

    def __init__(self):
        _workflow = StateGraph(State)
        _workflow.add_node("start", self.start)
        _workflow.add_node("buddy", self.the_buddy)
        _workflow.add_node("analyzer", self.the_analyzer)
        _workflow.add_node("guardian", self.the_guardian)
        _workflow.add_edge("start", "analyzer")
        _workflow.add_edge("start", "buddy")
        _workflow.add_edge("start", "guardian")
        _workflow.add_edge("buddy", END)
        _workflow.add_edge("analyzer", END)
        _workflow.add_edge("guardian", END)
        _workflow.set_entry_point("start")
        self._workflow = _workflow

    @property
    def graph(self) -> CompiledGraph:
        return self._workflow.compile()

    def start(self, state: State):
        return state

    def the_buddy(self, state: State):
        _prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=BUDDY_PROMPT),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )
        _conversation_llm = _prompt | self._llm(model="gpt-4o", temperature=0.8)
        _ai_message = _conversation_llm.invoke({"messages": state["messages"]})
        return {"messages": [_ai_message]}

    def the_analyzer(self, state: State):
        if "characteristics" not in state:
            state["characteristics"] = []
        _prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(
                    content=ANALYZER_PROMPT.format(
                        current_characteristics="\n-".join(state["characteristics"])
                    )
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )
        _extractor_llm = _prompt | self._llm(
            model="gpt-4o", temperature=0.8
        ).bind_tools([modify_characteristics], tool_choice="required")
        _res = _extractor_llm.invoke({"messages": state["messages"]})
        for _tool_call in _res.additional_kwargs.get("tool_calls", []):
            tool_call_id = _tool_call["id"]
            tool_call_args = json.loads(_tool_call["function"]["arguments"])
            tool_call_args["characteristics"] = state["characteristics"]
            modified_chars: ToolMessage = modify_characteristics.run(
                tool_input=tool_call_args, tool_call_id=tool_call_id
            )
            state["characteristics"] = modified_chars.content
        logger.info("Updated Characteristics: {}".format(state["characteristics"]))
        return state

    def the_guardian(self, state: State, config: dict):
        # Example to retrieve config variables in node
        # guardian_email = config.get("configurable", {}).get("guardian_email", None)
        _guardian_agent = create_react_agent(
            model=self._llm(model="gpt-4o", temperature=0.2),
            state_modifier=GUARDIAN_PROMPT,
            tools=[notify_dependents],
        )
        _guardian_agent.invoke({
            "messages": state["messages"]
        })
        return state

    def run(self, msg: str, guardian_email_input: Annotated[str, validate_email], thread_id: uuid.UUID):
        config = {"configurable": {"thread_id": thread_id, "guardian_email": guardian_email_input}}
        _res = self.graph.invoke({"messages": [HumanMessage(content=msg)]}, config)
        return _res
