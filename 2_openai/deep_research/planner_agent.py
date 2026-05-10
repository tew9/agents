from pydantic import BaseModel, Field
from agents import Agent 

HOW_MANY_SEARCHES = 2

# this agent will plan the search queries, ask for max clarifying questions before it produces the final search plan.
INSTRUCTIONS = f"You are a helpful research assistant. Given a query, ask a clarifying question to better understand the query \
  You can ask up to {HOW_MANY_SEARCHES} clarifying questions. Once you have asked enough clarifying questions, \
    produce a search plan with {HOW_MANY_SEARCHES} search queries that would be most helpful to answer the research question. \
      For each search query, provide your reasoning for why that search is important to answer the question."

class WebsearchItem(BaseModel):
    reason: str = Field(description="Your reasoning for why this search is important to the query.")
    query: str = Field(description="The search term to use for the web search.")
    
class WebSearchPlan(BaseModel):
    searches: list[WebsearchItem] = Field(description="A list of web searches to perform to best answer the query.")
    
planner_agent = Agent(
    name="PlannerAgent",
    instructions=INSTRUCTIONS,
    model="gpt-4o-mini",
    output_type=WebSearchPlan,
)

planner_tool = planner_agent.as_tool(tool_name="planner_tool", tool_description="A tool to plan the web searches to perform for a research query. Input is the research query, output is a search plan with the search queries to perform and the reasoning for each search.")