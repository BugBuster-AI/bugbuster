import { $api } from '@Common/api';
import { ERunStatus } from '@Entities/runs/models';
import {
    IChangeCasePosition,
    ICodegenArtifactResponse,
    ICodegenStatusResponse,
    IStartCaseRun,
    ITestCase,
    ITestCaseCreateFromRecordPayload,
    ITestCaseCreatePayload,
    ITestCaseUpdatePayload,
    TExecutionEngine
} from '@Entities/test-case/models';

export class TestCaseApi {
    private static instance: TestCaseApi | null

    public static getInstance (): TestCaseApi {
        if (!this.instance) {
            this.instance = new TestCaseApi()

            return this.instance
        }

        return this.instance
    }

    async create (data: ITestCaseCreatePayload): Promise<ITestCase> {
        return (await $api.post('content/case', data)).data
    }

    async createFromRecords (data: ITestCaseCreateFromRecordPayload): Promise<ITestCase> {
        return (await $api.post('content/generate_case_from_record', data)).data
    }

    async delete (id: string): Promise<void> {
        return (await $api.delete(`content/case/${id}`)).data
    }

    async getById (id: string): Promise<ITestCase> {
        return (await $api.get(`content/get_case_by_case_id?case_id=${id}`)).data
    }

    async update (data: ITestCaseUpdatePayload): Promise<ITestCase> {
        return (await $api.put('content/case', data)).data
    }

    async runCase (caseId: string, executionEngine: TExecutionEngine = 'vlm'): Promise<IStartCaseRun> {
        return (await $api.post(
            `runs?case_id=${caseId}&execution_engine=${executionEngine}`,
        )).data
    }

    async getPlaywrightCodegenStatus (caseId: string, runId: string): Promise<ICodegenStatusResponse> {
        return (await $api.get(`cases/${caseId}/codegen/playwright`, { params: { run_id: runId } })).data
    }

    async startPlaywrightCodegen (
        caseId: string,
        runId: string,
        maxValidationAttempts: number = 10,
    ): Promise<{ task_id: string; case_id: string; run_id: string }> {
        return (await $api.post(`cases/${caseId}/codegen/playwright`, {
            run_id: runId,
            max_validation_attempts: maxValidationAttempts,
        })).data
    }

    async getPlaywrightCodegenArtifact (caseId: string): Promise<ICodegenArtifactResponse> {
        return (await $api.get(`cases/${caseId}/codegen/playwright/artifact`)).data
    }

    async getPlaywrightCodegenArtifactById (
        caseId: string,
        artifactId: string,
    ): Promise<ICodegenArtifactResponse> {
        return (await $api.get(
            `cases/${caseId}/codegen/playwright/artifacts/${artifactId}`,
        )).data
    }

    async deletePlaywrightCodegenArtifact (caseId: string): Promise<{ deleted: boolean; artifact_id: string }> {
        return (await $api.delete(`cases/${caseId}/codegen/playwright/artifact`)).data
    }

    async clearPlaywrightCodegenJob (caseId: string): Promise<{ cleared: boolean }> {
        return (await $api.delete(`cases/${caseId}/codegen/playwright/job`)).data
    }

    async stopCase (runId: string): Promise<void> {
        return (await $api.delete(`runs?run_id=${runId}`)).data
    }

    async changePosition (data: IChangeCasePosition): Promise<{ status: string }> {
        return (await $api.put('content/change_case_position', null, { params: data })).data
    }

    async getTestTypes (): Promise<string[]> {
        return (await $api.get('content/list_case_types')).data
    }

    async deleteCasesById (ids: string[]): Promise<string[]> {
        return (await $api.delete('content/case', { data: ids })).data
    }

    async getTestFinalStatuses (): Promise<ERunStatus[]> {
        return (await $api.get('runs/list_final_statuses')).data
    }

    async copyCaseById (caseId: string[]): Promise<ITestCase[]> {
        return (await $api.post(`content/copy_case_by_case_id`, caseId)).data
    }
}
