import { useTestCaseStore } from '@Entities/test-case';
import { StepsCaseGroup } from '@Features/test-case/case-steps-group';

export const UntestedSteps = () => {
    const testCase = useTestCaseStore((state) => state.currentCase)

    return <StepsCaseGroup testCase={ testCase }/>
}
