import { $api } from '@Common/api';
import { ERunStatus } from '@Entities/runs/models';
import {
    IChangeCasePosition,
    IStartCaseRun,
    ITestCase,
    ITestCaseCreateFromRecordPayload,
    ITestCaseCreatePayload,
    ITestCaseUpdatePayload
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

    async runCase (caseId: string): Promise<IStartCaseRun> {

        //TODO: Узнать, почему в эндпоинте run_id
        return (await $api.post(`runs?case_id=${caseId}`)).data
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
