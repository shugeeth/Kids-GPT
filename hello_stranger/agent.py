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
from typing_extensions import Literal
from langchain_core.tools.structured import StructuredTool

from prompt import ENGAGE_USER_PROMPT, EXTRACT_CHARACTERISTICS_PROMPT, GENERATE_IMAGE_PROMPT

load_dotenv()

_checkpointer = MemorySaver()

class State(TypedDict):
    messages: Annotated[list, add_messages]
    characteristics: list[str]
    image_prompt: str

class Character(BaseModel):
    characteristics: list[str]

@tool
def modify_characteristics(operator: Literal["+", "-"], characteristic: str, characteristics: Annotated[list, InjectedState("characteristics")]) -> list[str]: # noqa
    """Modify the list of characteristics."""
    if operator == "+":
        characteristics.append(characteristic)
    elif operator == "-":
        characteristics.remove(characteristic)
    return characteristics

class Agent:
    _llm = ChatOpenAI

    def __init__(self):
        _workflow = StateGraph(State)
        _workflow.add_node("engage_user", self.engage_user)
        _workflow.add_node("extract_characteristics", self.extract_characteristics)
        _workflow.add_node("generate_image_prompt", self.generate_image_prompt)
        _workflow.add_node("generate_image", self.generate_image)
        _workflow.add_edge("engage_user", "extract_characteristics")
        _workflow.add_conditional_edges("extract_characteristics",
                                        lambda state: state["characteristics"].__len__() > 0,
                                        {True: "generate_image_prompt", False: END})
        _workflow.add_edge("generate_image_prompt", "generate_image")
        _workflow.add_edge("engage_user", END)
        _workflow.add_edge(START, "engage_user")
        _workflow.set_entry_point("engage_user")
        self._workflow = _workflow

    @property
    def graph(self) -> CompiledGraph:
        return self._workflow.compile(checkpointer=_checkpointer)

    def engage_user(self, state: State):
        _prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=ENGAGE_USER_PROMPT),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )
        _conversation_llm = _prompt | self._llm(model="gpt-4o", temperature=0.8)
        _ai_message = _conversation_llm.invoke({"messages": state["messages"]})
        return {"messages": [_ai_message]}

    def extract_characteristics(self, state: State):
        if "characteristics" not in state:
            state["characteristics"] = []
        _prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=EXTRACT_CHARACTERISTICS_PROMPT),
                MessagesPlaceholder(variable_name="messages"),
            ]
        ).partial(current_characteristics="\n-".join(state["characteristics"]))
        _extractor_llm = _prompt | self._llm(model="gpt-4o", temperature=0.5).bind_tools([modify_characteristics], tool_choice="required")
        _res = _extractor_llm.invoke({"messages": state["messages"]})
        for _tool_call in _res.additional_kwargs["tool_calls"]:
            tool_call_id = _tool_call["id"]
            tool_call_args = json.loads(_tool_call["function"]["arguments"])
            tool_call_args["characteristics"] = state["characteristics"]
            modified_chars: ToolMessage = modify_characteristics.run(tool_input=tool_call_args, tool_call_id=tool_call_id)
            state["characteristics"] = modified_chars.content
        print("Updated Characteristics:")
        print(state["characteristics"])
        return state

    def generate_image_prompt(self, state: State):
        _prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=GENERATE_IMAGE_PROMPT),
            ]
        )
        _conversation_llm = _prompt | self._llm(model="gpt-4o", temperature=0.8)
        _ai_message = _conversation_llm.invoke({"characteristics": state["characteristics"]})
        print("Image Prompt:")
        print(_ai_message.content)
        state["image_prompt"] = _ai_message.content
        return state

    def generate_image(self, state: State):
        with OpenAI() as client:
            response = client.images.generate(
                model="dall-e-3",
                prompt=state["image_prompt"],
                size="1024x1024",
                quality="standard",
                n=1,
            )
            image_url = response.data[0].url

        image_data = requests.get(image_url).content
        os.makedirs("images", exist_ok=True)
        with open("images/image.png", "wb") as f:
            f.write(image_data)

    def run(self, msg: str, config: dict):
        return self.graph.invoke({
                                    "messages": [HumanMessage(content=msg)]
                                    },
                                 config)

if __name__ == "__main__":
    agent = Agent()
    _config = {"configurable": {"thread_id": uuid.uuid4()}}
    while True:
        _msg = input("Ask: ")
        res = agent.run(_msg, _config)
        print("="*10)
        print(res["messages"][-1].content)
        print("="*10)





