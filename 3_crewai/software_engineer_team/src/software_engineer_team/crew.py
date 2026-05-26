from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from pydantic import BaseModel, Field
from typing import Literal


# ---------------------------------------------------------------------------
# Pydantic schemas — structured handoffs for design tasks.
# Code-generating tasks (backend_task, unit_tests_task, frontend_task)
# produce real files via agent tools; their outputs travel as free-form
# task context through context=[...] edges.
# ---------------------------------------------------------------------------

class EndpointSpec(BaseModel):
    method: str = Field(description="HTTP method e.g. GET, POST")
    path: str = Field(description="URL path e.g. /items/{id}")
    request_schema: str = Field(description="Pydantic model name for request body")
    response_schema: str = Field(description="Pydantic model name for response body")
    authz_scope: str = Field(default="", description="Required auth scope or role")


class ModuleSpec(BaseModel):
    name: str = Field(description="Python module path e.g. backend.services.items")
    purpose: str = Field(description="What this module is responsible for")
    public_surface: list[str] = Field(default_factory=list, description="Exported function/class names")


class EntitySpec(BaseModel):
    name: str = Field(description="Entity/table name")
    fields: list[str] = Field(description="Field names and types e.g. 'id: int'")
    relations: list[str] = Field(default_factory=list, description="FK relations e.g. 'order has many items'")


class UIPage(BaseModel):
    name: str = Field(description="Page name")
    components: list[str] = Field(description="Gradio component types on this page")
    primary_flow: str = Field(description="Main user action on this page")


class NonFunctionalRequirements(BaseModel):
    performance: str = Field(default="")
    security: str = Field(default="")
    scalability: str = Field(default="")


class SystemDesign(BaseModel):
    overview: str = Field(description="1-2 sentence summary of what is being built")
    modules: list[ModuleSpec] = Field(description="Backend module decomposition")
    data_model: list[EntitySpec] = Field(description="Database entities")
    api_contract: list[EndpointSpec] = Field(description="Every API endpoint")
    nfr: NonFunctionalRequirements = Field(default_factory=NonFunctionalRequirements)
    ui_spec: list[UIPage] = Field(description="UI pages and their components")
    risks: list[str] = Field(default_factory=list)


class TestCase(BaseModel):
    id: str = Field(description="Stable id e.g. TC-ITEMS-01")
    area: str = Field(description="Feature area e.g. items, auth")
    description: str
    preconditions: str
    steps: list[str]
    expected_result: str
    priority: Literal["P0", "P1", "P2"] = "P1"


class CoverageRow(BaseModel):
    requirement_id: str
    test_ids: list[str]


class TestPlan(BaseModel):
    test_cases: list[TestCase]
    coverage_matrix: list[CoverageRow]


class ComponentSpec(BaseModel):
    name: str
    type: str = Field(description="Gradio component type e.g. gr.Textbox")
    page: str = Field(description="Page this component lives on")
    bound_to: str = Field(default="", description="Backend service function it calls")


class StyleTokens(BaseModel):
    palette: list[str] = Field(default_factory=list, description="Entries like 'primary=#3B82F6'")
    typography: list[str] = Field(default_factory=list, description="Entries like 'heading=Inter 24px bold'")
    spacing: list[str] = Field(default_factory=list, description="Entries like 'section_gap=2rem'")


class FrontendSpec(BaseModel):
    pages: list[UIPage]
    components: list[ComponentSpec]
    style_tokens: StyleTokens = Field(default_factory=StyleTokens)
    interaction_map: list[str] = Field(default_factory=list, description="Event -> handler descriptions")


class ReviewReport(BaseModel):
    status: Literal["PASS", "PASS_WITH_NOTES", "BLOCK"]
    contract_diff: list[str] = Field(default_factory=list, description="T0 vs T1 API contract mismatches")
    coverage_gaps: list[str] = Field(default_factory=list, description="Requirements with no test")
    regression_gaps: list[str] = Field(default_factory=list, description="P0 cases not in regression set")
    security_failures: list[str] = Field(default_factory=list)
    wired_endpoint_gaps: list[str] = Field(default_factory=list, description="Endpoints missing from Gradio app")
    summary_markdown: str = Field(description="Human-readable review summary")


# ---------------------------------------------------------------------------
# Crew
# ---------------------------------------------------------------------------

@CrewBase
class SoftwareEngineerTeam():
    """SoftwareEngineerTeam crew"""

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    # -----------------------------------------------------------------------
    # Agents
    # -----------------------------------------------------------------------

    @agent
    def backend_engineer(self) -> Agent:
        return Agent(
            config=self.agents_config['backend_engineer'],
            verbose=True,
            allow_code_execution=True,
            code_execution_mode="safe",
            max_execution_time=60,
            max_retry_limit=3,
        )

    @agent
    def frontend_engineer(self) -> Agent:
        return Agent(
            config=self.agents_config['frontend_engineer'],
            allow_code_execution=True,
            code_execution_mode="safe",
            max_execution_time=60,
            max_retry_limit=3,
        )

    @agent
    def qa_engineer(self) -> Agent:
        return Agent(
            config=self.agents_config['qa_engineer'],
            verbose=True,
        )

    @agent
    def unit_test_engineer(self) -> Agent:
        return Agent(
            config=self.agents_config['unit_test_engineer'],
            allow_code_execution=True,
            code_execution_mode="safe",
            max_execution_time=60,
            max_retry_limit=3,
        )

    # -----------------------------------------------------------------------
    # Tasks
    # -----------------------------------------------------------------------

    @task
    def design_task(self) -> Task:
        return Task(
            config=self.tasks_config['design_task'],
        )

    @task
    def backend_task(self) -> Task:
        return Task(
            config=self.tasks_config['backend_task'],
        )

    @task
    def design_test_task(self) -> Task:
        return Task(
            config=self.tasks_config['design_test_task'],
        )

    @task
    def test_design_frontend(self) -> Task:
        return Task(
            config=self.tasks_config['test_design_frontend'],
        )

    @task
    def unit_tests_task(self) -> Task:
        return Task(
            config=self.tasks_config['unit_tests_task'],
        )

    @task
    def frontend_task(self) -> Task:
        return Task(
            config=self.tasks_config['frontend_task'],
        )

    @task
    def architect_review(self) -> Task:
        return Task(
            config=self.tasks_config['architect_review'],
        )

    @agent
    def architect_lead(self) -> Agent:
        return Agent(
            config=self.agents_config['architect_lead'],
            allow_delegation=True,
        )

    # -----------------------------------------------------------------------
    # Crew
    # -----------------------------------------------------------------------

    @crew
    def crew(self) -> Crew:
        """Creates the SoftwareEngineerTeam crew"""

        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            output_log_file="output/run.log",
        )
