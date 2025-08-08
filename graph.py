from langgraph.graph import StateGraph,START,END
from pydantic import BaseModel
from typing import TypedDict, Literal
from openai import AzureOpenAI
from langgraph.prebuilt import create_react_agent
import redis
import json
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os
from langchain_core.messages import HumanMessage
import gradio as gr

load_dotenv(override=True)

class User(BaseModel):
    user_id : str 
    user_name : str
    user_phone : str
    user_email : str
    on_call_role :Literal['primary', 'secondary', 'SRE', 'manager']
    permissions : Literal['triage', 'escalate', 'close', 'on-call-level', 'view']
    team : str
    metadata : dict[str, str]

class GraphState(TypedDict):
    session_id: str
    user : User
    userQuery: str
    query: str
    response: str
    next_action: str
    cur_node: str
    context: dict[str, str]


class azure_client:
    def __init__(self):
        self.llm = self._initialize_azure_client()

    def _initialize_azure_client(self) -> AzureOpenAI:
       

        # Azure OpenAI Configuration
        AZURE_OPENAI_ENDPOINT="https://sanny-mini.openai.azure.com/"
        AZURE_OPENAI_API_KEY="api"
        AZURE_OPENAI_API_VERSION="2025-01-01-preview"
        AZURE_OPENAI_DEPLOYMENT_NAME="gpt-4o-mini"

        client = AzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
            azure_endpoint=AZURE_OPENAI_ENDPOINT
        )
        return client

class redisClient:
    redis=None
    def __init__(self):
        if self.redis == None:
            #self.redis=redis.StrictRedis(host="sandiskurl",port=0000, db=4 , decode_responses=True)
            self.redis=redis.StrictRedis(host='localhost', port=6379,  decode_responses=True)

async def superviser_agent(state: GraphState)->GraphState:

    llm= ChatOpenAI(model="gpt-4o-mini",api_key=os.getenv("OPENAI_API_KEY"))

    agent=create_react_agent(model=llm,tools=[])

    response=await agent.ainvoke({"messages": [HumanMessage(content=state["query"])]})
    
    # print(response["messages"][-1].content)

    state["response"]=response["messages"][-1].content

    return state

def saveMemoryNode(state: GraphState) -> GraphState:
    redis_conn = redisClient().redis
    session_id = state["session_id"]

    new_message = {
        "UserMessage": state["userQuery"],
        "AIMessage": state["response"]
    }

    existing_data = redis_conn.get(session_id)
    if existing_data:
        messages = json.loads(existing_data)
    else:
        messages = []

    messages.append(new_message)
    redis_conn.set(session_id, json.dumps(messages))

    return state


def getMemoryNode(state: GraphState) -> GraphState:
    redis_conn = redisClient().redis
    session_id = state["session_id"]

    existing_data = redis_conn.get(session_id)
    if existing_data:
        messages = json.loads(existing_data)
    else:
        messages = []

    context_lines = ["This is the context of the conversation:\n"]

    for message in messages:
        context_lines.append(f"User: {message['UserMessage']}")
        context_lines.append(f"AI: {message['AIMessage']}")
        context_lines.append("")

    context_lines.append(f"Current query: {state['userQuery']}")
    modified_prompt = "\n".join(context_lines)

    state["query"] = modified_prompt
    return state


graphBuilder = StateGraph(GraphState)

graphBuilder.set_entry_point("getMemoryNode")

graphBuilder.add_node("superviser_agent",superviser_agent)
graphBuilder.add_node("saveMemoryNode",saveMemoryNode)
graphBuilder.add_node("getMemoryNode",getMemoryNode)


graphBuilder.add_edge("getMemoryNode","superviser_agent")
graphBuilder.add_edge("superviser_agent","saveMemoryNode")
graphBuilder.add_edge("saveMemoryNode",END)

graph = graphBuilder.compile()

if __name__ == "__main__":
    import asyncio

    async def main():
        config = {"configurable": {"thread_id": "1"}}
        while True:
            user_input = input("ask: ")
            initial_state = {
                "session_id": "10",               # use thread_id or user ID
                "user": {                          # minimal dummy user object
                    "user_id": "1",
                    "user_name": "test_user",
                    "user_phone": "0000000000",
                    "user_email": "test@example.com",
                    "on_call_role": "primary",
                    "permissions": "triage",
                    "team": "test_team",
                    "metadata": {}
                },
                "userQuery": user_input,          # pass the raw input here
                "query": user_input,                      # will be modified in getMemoryNode
                "response": "",
                "next_action": "",
                "cur_node": "",
                "context": {}
            }
            if user_input == "exit":
                break

            result = await graph.ainvoke(initial_state,config=config)
            print(result["response"])
        # async def chat(user_input: str, history):
        #     config = {"configurable": {"thread_id": "10"}}
        #     initial_state = {
        #         "session_id": "10",               # use thread_id or user ID
        #         "user": {                          # minimal dummy user object
        #             "user_id": "1",
        #             "user_name": "test_user",
        #             "user_phone": "0000000000",
        #             "user_email": "test@example.com",
        #             "on_call_role": "primary",
        #             "permissions": "triage",
        #             "team": "test_team",
        #             "metadata": {}
        #         },
        #         "userQuery": user_input,          # pass the raw input here
        #         "query": user_input,                      # will be modified in getMemoryNode
        #         "response": "",
        #         "next_action": "",
        #         "cur_node": "",
        #         "context": {}
        #     }
        #     result =await graph.ainvoke(initial_state,config=config)
        #     return result["response"]


        # gr.ChatInterface(chat, type="messages").launch()

    asyncio.run(main())