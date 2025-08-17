from pydantic import BaseModel
from typing import TypedDict, Literal,Annotated
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, BaseMessage,AnyMessage
from langgraph.graph import StateGraph,START,END
from langgraph.graph.message import add_messages
from langchain_openai import AzureChatOpenAI
import asyncio
from dotenv import load_dotenv
from langgraph.checkpoint.redis import RedisSaver
import os
import redis
from checkpointer import CustomPostgresSaver
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
    # userQuery: str
    # query: str
    response: str
    next_action: str
    cur_node: str
    messages: Annotated[list[AnyMessage], add_messages]


##################################
def superviser_agent(state: GraphState) -> GraphState:

    llm = AzureChatOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_deployment=os.getenv("AZURE_DEPLOYMENT_NAME"),
        openai_api_version=os.getenv("AZURE_API_VERSION")
    )
    
    global redis_checkpointer
    agent = create_react_agent(model=llm, tools=[], checkpointer=redis_checkpointer)

    config = {"configurable": {"thread_id": state["session_id"]}}
    response = agent.invoke({"messages": state["messages"]}, config=config)
    state["response"] = response["messages"][-1].content
    return state

graphBuilder = StateGraph(GraphState)
graphBuilder.set_entry_point("superviser_agent")
graphBuilder.add_node("superviser_agent", superviser_agent)
graphBuilder.add_edge("superviser_agent", END)

def main(graph):
    global redis_checkpointer
    redis_client=redis.StrictRedis(host='localhost', port=6379,  decode_responses=True)

    ttl_config = {
        "default_ttl": 1,     # Increased TTL for better context retention
        "refresh_on_read": True,
    }

    with RedisSaver.from_conn_string(redis_client=redis_client, ttl=ttl_config) as _redis_checkpointer:
        _redis_checkpointer.setup()
        redis_checkpointer = _redis_checkpointer
        
        while True:
            userinput = input("ask: ")
            
            if userinput == "exit":
                break
                
            inputs = [HumanMessage(content=userinput)]
            initial_state = {
                "session_id": "1",               
                "user": {
                    "user_id": "1",
                    "user_name": "test_user",
                    "user_phone": "0000000000",
                    "user_email": "test@example.com",
                    "on_call_role": "primary",
                    "permissions": "triage",
                    "team": "test_team",
                    "metadata": {}
                },                 
                "response": "",
                "next_action": "",
                "cur_node": "",
                "messages": inputs
            }

            config = {"configurable": {"thread_id": initial_state["session_id"]}}
            response = graph.invoke(initial_state, config=config)
            print(response["response"])

if __name__ == "__main__":
    
    with CustomPostgresSaver.from_conn_string(conn_string=os.getenv("POSTGRESQL_CONNECTION_STRING")) as checkpointer:
        checkpointer.setup()  # Create the necessary database tables
        graph= graphBuilder.compile(checkpointer=checkpointer)
        main(graph=graph)