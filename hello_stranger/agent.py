import json
import os
import uuid
from typing import TypedDict, Annotated

import requests
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool, BaseTool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END, add_messages
from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt import InjectedState
from openai import OpenAI
from pydantic import BaseModel
from pydantic.v1 import UUID4
from typing_extensions import Literal
from langchain_core.tools.structured import StructuredTool
from tool import modify_characteristics, notify_dependents
from langgraph.prebuilt import create_react_agent
from util import characteristics_reducer
from logger_setup import logger

from prompt import BUDDY_PROMPT, ANALYZER_PROMPT, GUARDIAN_PROMPT

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
        return self._workflow.compile(checkpointer=_checkpointer)

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
                SystemMessage(content=ANALYZER_PROMPT.format(current_characteristics="\n-".join(state["characteristics"]))),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )
        _extractor_llm = _prompt | self._llm(model="gpt-4o", temperature=0.5).bind_tools([modify_characteristics])
        _res = _extractor_llm.invoke({"messages": state["messages"]})
        for _tool_call in _res.additional_kwargs.get("tool_calls", []):
            tool_call_id = _tool_call["id"]
            tool_call_args = json.loads(_tool_call["function"]["arguments"])
            tool_call_args["characteristics"] = state["characteristics"]
            modified_chars: ToolMessage = modify_characteristics.run(tool_input=tool_call_args, tool_call_id=tool_call_id)
            state["characteristics"] = modified_chars.content
        logger.debug("Updated Characteristics:")
        logger.debug(state["characteristics"])
        return state

    def the_guardian(self, state: State):
        _guardian_agent = create_react_agent(model=self._llm(model="gpt-4o", temperature=0.2),
                                           state_modifier=GUARDIAN_PROMPT,
                                           tools=[notify_dependents])
        _guardian_agent.invoke({"messages": state["messages"]})
        return state

    def run(self, msg: str, thread_id: uuid.UUID):
        config = {"configurable": {"thread_id": thread_id}}
        return self.graph.invoke({
                                    "messages": [HumanMessage(content=msg)]
                                    },
                                 config)
