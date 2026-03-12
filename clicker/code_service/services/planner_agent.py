from typing import List

from openai import AsyncOpenAI
from pydantic import BaseModel

from config import logger
from code_service.code_service_config import CodeServiceConfig
from code_service.models import ExecutionPlan, PlanStep, PlanStepStatus
from code_service.services.prompt_loader import PromptLoader


class PlanStepSchema(BaseModel):
    instruction: str


class PlanSchema(BaseModel):
    steps: List[PlanStepSchema]


class PlannerAgent:
    def __init__(
        self,
        openai_client: AsyncOpenAI,
        config: CodeServiceConfig,
    ):
        self.openai_client = openai_client
        self.config = config
        self.system_prompt_name = "planner_system_prompt.txt"

    async def create_plan(self, instruction: str) -> ExecutionPlan:
        system_prompt = PromptLoader._load_prompt_template(self.system_prompt_name)

        if not system_prompt:
            system_prompt = self._get_default_system_prompt()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Create a step-by-step plan for the following task:\n\n{instruction}"}
        ]

        try:
            response = await self.openai_client.beta.chat.completions.parse(
                model=self.config.llm.model,
                messages=messages,
                response_format=PlanSchema,
                temperature=self.config.llm.temperature,
                max_tokens=self.config.llm.max_tokens,
            )

            plan_response = response.choices[0].message.parsed

            steps = [
                PlanStep(
                    index=i,
                    instruction=step.instruction,
                    status=PlanStepStatus.PENDING
                )
                for i, step in enumerate(plan_response.steps)
            ]

            execution_plan = ExecutionPlan(
                original_instruction=instruction,
                steps=steps
            )

            logger.info(f"Created execution plan with {len(steps)} steps")
            for step in steps:
                logger.info(f"  Step {step.index + 1}: {step.instruction}")

            return execution_plan

        except Exception as e:
            logger.error(f"Error creating plan: {str(e)}")
            single_step = PlanStep(
                index=0,
                instruction=instruction,
                status=PlanStepStatus.PENDING
            )
            return ExecutionPlan(
                original_instruction=instruction,
                steps=[single_step]
            )

    def _get_default_system_prompt(self) -> str:
        return """You are a task planning assistant. Your job is to break down user instructions into clear, atomic steps.

Rules for creating steps:
1. Each step should be a single, atomic action
2. Steps should be in logical order
3. Each step should be clear and specific
4. Avoid combining multiple actions in one step
5. Include verification steps when needed

Example:
Task: "Login to the website and check my orders"
Steps:
1. Navigate to the login page
2. Enter username in the login form
3. Enter password in the login form
4. Click the login button
5. Navigate to the orders section
6. Verify the orders list is displayed"""
