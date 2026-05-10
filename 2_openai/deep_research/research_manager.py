from agents import Agent, Runner, trace, gen_trace_id
from search_agent import search_tool
from writter_agent import writter_tool, ReportData
from planner_agent import planner_tool, WebsearchItem, WebSearchPlan
from email_agent import email_agent
from agents import Agent
import asyncio

tools = [planner_tool, search_tool, writter_tool]
handoff = [email_agent]
INSTRUCTIONS = """You are a research manager agent. Your job is to manage the process of doing deep research for a given query.\
You will first create a plan for how to research the query, then you will execute that plan, and finally you will send out an email with the final report. You should use the tools at your disposal to accomplish this task. iteratively use the tools you have at your disposal in the appropriate order to complete the research process. and then send the email."""

research_manager = Agent(
    name="Research Manager",
    instructions=INSTRUCTIONS,
    model="gpt-4o-mini",
    tools=tools,
    handoffs=handoff,
)

class ResearchManager:
    
    async def run(self, query: str):
        """ Run the deep research process, yielding the status updateds and the final report"""
        trace_id = gen_trace_id()
        with trace("Research trace", trace_id=trace_id):
            print(f"View trace: https://platform.openai.com/traces/trace?trace_id={trace_id}")
            yield f"View trace: https://platform.openai.com/traces/trace?trace_id={trace_id}"
            print("Starting the search...")
            response = await Runner.run(research_manager, query)
            print(f"Research manager finished running with response: {response}")
            print("Research complete!")
            yield "Research complete!"
            if response.final_output is not None:
                report = response.final_output_as(ReportData)
                print("Final report:")
                yield report
                
            # search_plan = await self.plan_research(query) # get the search plan
            # yield "Searches planned, starting to search..."
            # search_results = await self.perform_searches(search_plan) # perform the searches
            # yield "Searches complete, starting to write the report..."
            # report = await self.write_report(query, search_results) # write the report
            # yield "Report written, sending the email..."
            # await self.send_email(report) # send the report via email
            # yield "Email sent, research complete!"
            # yield report.markdown_report # yield the final report as well
            
            
    # async def plan_research(self, query: str) -> WebSearchPlan:
    #     """ Plan the searches to perform for the query"""
    #     print("Planning the research...")
    #     result = await Runner.run(
    #         planner_tool,
    #         f"query: {query}",
    #     )
    #     print(f"Will perform {len(result.final_output.searches)} searches.")
    #     return result.final_output_as(WebSearchPlan)
      
    
    # async def perform_searches(self, search_plan: WebSearchPlan) -> list[str]:
    #     """ Perform the searches to perform for the query"""
    #     print("Searching...")
    #     num_completed = 0
    #     tasks =[asyncio.create_task(self.search(item)) for item in search_plan.searches]
    #     results = []
    #     for task in asyncio.as_completed(tasks):
    #         result = await task
    #         if result is not None:
    #             results.append(result)
    #         num_completed += 1
    #         print(f"Searching... {num_completed}/{len(search_plan.searches)} completed.")
    #     print("Finished searching")
    #     return results
      
    # async def search(self, item: WebsearchItem) -> str | None:
    #     """ Perform a search for the query"""
    #     input = f"Search term: {item.query}\nReasoning: {item.reason}"
    #     try:
    #         result = await Runner.run(search_agent, input)
    #         return str(result.final_output)
    #     except Exception as e:
    #         return None
          
    # async def write_report(self, query: str, search_results: list[str]) -> ReportData:
    #     """ Write the report for the query"""
    #     print("Thinking about the report...")
    #     input = f"Original query: {query}\nSummarized search results:\n{search_results}"
    #     result = await Runner.run(writter_agent, input)
    #     print("Finished writing the report.")
    #     return result.final_output_as(ReportData)
      
    # async def send_email(self, report: ReportData) -> None:
    #     print("Writing email...")
    #     result = await Runner.run(
    #       email_agent,
    #       report.markdown_report
    #     )
    #     print("Email sent.")
    #     return report
        