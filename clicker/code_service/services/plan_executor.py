from typing import Optional, Any

from config import logger
from code_service.models import ExecutionPlan, PlanStepStatus
from code_service.services.browser_state_agent import BrowserAgent


class PlanExecutor:
    def __init__(
        self,
        playwright: Any,
        browser: Any,
        page: Any,
    ):
        self.playwright = playwright
        self.browser = browser
        self.page = page
        self.browser_agent = BrowserAgent(
            playwright=playwright,
            browser=browser,
            page=page
        )

    async def execute_plan(self, plan: ExecutionPlan) -> ExecutionPlan:
        logger.info(f"Starting plan execution: {plan.original_instruction}")
        logger.info(f"Total steps: {len(plan.steps)}")

        self.browser_agent.set_plan(plan)

        for step_index, step in enumerate(plan.steps):
            plan.current_step_index = step_index
            step.status = PlanStepStatus.IN_PROGRESS

            logger.info(f"\n{'='*50}")
            logger.info(f"Executing step {step_index + 1}/{len(plan.steps)}")
            logger.info(f"Instruction: {step.instruction}")
            logger.info(f"{'='*50}")

            try:
                result = await self.browser_agent.run_with_steps(step.instruction, plan)

                step.status = PlanStepStatus.COMPLETED
                step.result_summary = result if result else "Step completed successfully"
                logger.info(f"Step {step_index + 1} completed successfully")

            except Exception as e:
                step.status = PlanStepStatus.FAILED
                step.error_message = str(e)
                logger.error(f"Step {step_index + 1} failed: {str(e)}")

                return plan

        logger.info(f"Plan execution completed. All {len(plan.steps)} steps finished.")
        return plan

    async def execute_single_step(
        self,
        plan: ExecutionPlan,
        step_index: int
    ) -> ExecutionPlan:
        if step_index < 0 or step_index >= len(plan.steps):
            raise ValueError(f"Invalid step index: {step_index}")

        plan.current_step_index = step_index
        step = plan.steps[step_index]
        step.status = PlanStepStatus.IN_PROGRESS

        self.browser_agent.set_plan(plan)

        try:
            result = await self.browser_agent.run_with_steps(step.instruction, plan)
            step.status = PlanStepStatus.COMPLETED
            step.result_summary = result if result else "Step completed successfully"

        except Exception as e:
            step.status = PlanStepStatus.FAILED
            step.error_message = str(e)
            logger.error(f"Step {step_index + 1} failed: {str(e)}")

        return plan

    def get_plan_status(self, plan: ExecutionPlan) -> dict:
        completed = sum(1 for s in plan.steps if s.status == PlanStepStatus.COMPLETED)
        failed = sum(1 for s in plan.steps if s.status == PlanStepStatus.FAILED)
        pending = sum(1 for s in plan.steps if s.status == PlanStepStatus.PENDING)
        in_progress = sum(1 for s in plan.steps if s.status == PlanStepStatus.IN_PROGRESS)

        return {
            "total": len(plan.steps),
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "in_progress": in_progress,
            "success": failed == 0 and pending == 0 and in_progress == 0
        }
