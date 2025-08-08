from pydantic import BaseModel
from typing import TypedDict, Literal,Annotated
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, BaseMessage,AnyMessage
from langgraph.graph import StateGraph,START,END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.redis import RedisSaver, AsyncRedisSaver
import asyncio
from dotenv import load_dotenv
import os
import redis
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


def superviser_agent(state: GraphState)->GraphState:

    llm= ChatOpenAI(model="gpt-4o-mini",api_key=os.getenv("OPENAI_API_KEY"))

    agent=create_react_agent(model=llm,tools=[])
    
    #print(state["messages"])
    response= agent.invoke({"messages":state["messages"]})
    # print("___________________ \n ", type(response["messages"][-1].content))
    # print(response["messages"][-1].content)

    state["response"]=response["messages"][-1].content
    # print("___________________ \n",state)

    return state



graphBuilder = StateGraph(GraphState)
graphBuilder.set_entry_point("superviser_agent")
graphBuilder.add_node("superviser_agent",superviser_agent)
graphBuilder.add_edge("superviser_agent",END)


#################################################
# uncomment this to use localhost url

# ttl_config = {
#     "default_ttl": 10,     # Default TTL in minutes
#     "refresh_on_read": True,  # Refresh TTL when checkpoint is read
# }
# REDIS_URI = "redis://localhost:6379"
# checkpointer = None
# with RedisSaver.from_conn_string(REDIS_URI,ttl=ttl_config) as _checkpointer:
#     _checkpointer.setup()
#     checkpointer=_checkpointer
    

####################################
# replace below host to there redis url 
# redis_clinet=redis.StrictRedis(host='localhost', port=6379 ,db = 4, decode_responses=True)
redis_clinet=redis.StrictRedis(host='localhost', port=6379,  decode_responses=True)

ttl_config = {
    "default_ttl": 10,     # Default TTL in minutes
    "refresh_on_read": True,  # Refresh TTL when checkpoint is read
}
checkpointer = None
with RedisSaver.from_conn_string(redis_client=redis_clinet,ttl=ttl_config) as _checkpointer:
    _checkpointer.setup()
    checkpointer=_checkpointer

##################################
graph = graphBuilder.compile(checkpointer=checkpointer)

def main():

    while True:
        userinput=input("aks: ")
        inputs= [HumanMessage(content=userinput)]
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
                # "userQuery": userinput,
                # "query": userinput,                      
                "response": "",
                "next_action": "",
                "cur_node": "",
                "context": {},
                "messages":inputs
            }
        if userinput == "exit":
            break

        config = {"configurable": {"thread_id": initial_state["session_id"]}}
        response= graph.invoke(initial_state,config=config)
        print(response["response"])
        # for event in graph.stream(initial_state,config=config, stream_mode= "values"):
        #     event["response"]
        

if __name__ == "__main__":

    main()