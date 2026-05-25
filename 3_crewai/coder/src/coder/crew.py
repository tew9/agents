from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

@CrewBase
class Coder():
    """Coder crew"""

    agents: list[BaseAgent]
    tasks: list[Task]

    @agent
    def coder(self) -> Agent:
        return Agent(
            config=self.agents_config['coder'], 
            verbose=True,
            allow_code_execution=True, # Enable code execution for this agent
            code_execution="safe", #use docker environment for isolated execution 
            max_execution_time=30, # 30sec
            max_retry_limit=3, # Retry up to 3 times if code execution fails
        )

    @task
    def coder_task(self) -> Task:
        return Task(config=self.tasks_config['coder_task'])

    @crew
    def crew(self) -> Crew:
        """Creates the Coder crew"""
    
        return Crew(
            agents=self.agents, # Automatically created by the @agent decorator
            tasks=self.tasks, # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
        )
