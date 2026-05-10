from pydantic import BaseModel, Field 
from agents import Agent 

INSTRUCTIONS = (
    "You are a senior researcher tasked with writing a cohesive report for a research query. "
    "You will be provided with the original query, and some initial research done by a research assistant.\n"
    "You should first come up with an outline for the report that describes the structure and "
    "flow of the report. Then, generate the report and return that as your final output.\n"
    "The final output should be in markdown format, and it should be lengthy and detailed. Aim "
    "for 5-10 pages of content, at least 1000 words."
)

class ReportData(BaseModel):
    short_summary: str = Field(description="A short 2-3 sentence summary of the findings.")
    markdown_report: str = Field(description="The full report in markdown format.")
    follow_up_questions: list[str] = Field(description="Suggested topics to research further")
    
writter_agent = Agent(
    name="Writter Agent",
    instructions=INSTRUCTIONS,
    model="gpt-4o-mini",
    output_type=ReportData,
)

writter_tool = writter_agent.as_tool(tool_name="writter_tool", tool_description="A tool to write a detailed report for a research query. Input is the original research query and the summarized search results, output is a detailed report in markdown format.")