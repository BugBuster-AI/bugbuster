import { $api } from '@Common/api';
import {
    ICreateGroupedRunPayload, ICreateGroupedRunResponse, IDeleteCasesFromGroup,
    IGetRunsPayload,
    IGroupedRunsParams, IGroupRunList,
    IRunById,
    IRunList,
    IStartGroupedRunResponse,
    IStopGroupedRunResponse
} from '@Entities/runs/models';
import { ICompleteRunDto } from '@Entities/runs/models/complete-run.dto';
import { IPassStepDto, IPassStepResponse } from '@Entities/runs/models/pass-step.dto';
import { IStartGroupRunDto } from '@Entities/runs/models/start-group-run.ts';

export class RunApi {
    private static instance: RunApi | null

    public static getInstance (): RunApi {
        if (!this.instance) {
            this.instance = new RunApi()

            return this.instance
        }

        return this.instance
    }

    async getRunById (runId: string): Promise<IRunById> {
        return (await $api.get(`runs/${runId}`)).data
    }

    async getRuns (params?: IGetRunsPayload): Promise<IRunList> {
        return (await $api.get('runs', { params })).data
    }

    async getGroupedRuns (params?: IGroupedRunsParams): Promise<IGroupRunList> {
        return (await $api.get('runs/group_runs/', {
            params, paramsSerializer: {
                indexes: null,
            }
        })).data
    }

    async startGroupedRun (data: IStartGroupRunDto): Promise<IStartGroupedRunResponse> {
        const { runIds, ...params } = data || {}

        return (await $api.post(`runs/group_runs/start_run_by_group_run_id`, runIds, {
            params
        })).data
    }

    async stopGroupedRun (id: string): Promise<IStopGroupedRunResponse> {
        return (await $api.delete(`runs/group_runs/stop_run_by_group_run_id?group_run_id=${id}`)).data
    }

    async createGroupedRun (data: ICreateGroupedRunPayload): Promise<ICreateGroupedRunResponse> {
        return (await $api.post('runs/group_runs', data)).data
    }

    async editGroupedRun (id: string, data: ICreateGroupedRunPayload): Promise<ICreateGroupedRunResponse> {
        return (await $api.put(`runs/group_runs?group_run_id=${id}`, data)).data
    }

    async getListStatuses (): Promise<string[]> {
        return (await $api.get('runs/list_statuses')).data
    }

    async deleteCasesFromGroup (data: IDeleteCasesFromGroup): Promise<string> {
        const { runId, case_ids } = data || {}

        return (await $api.delete(`runs/delete_cases_in_group_run?group_run_id=${runId}`, {
            data: case_ids
        })).data
    }

    async passCaseStepInRun (data: IPassStepDto): Promise<IPassStepResponse> {
        return (await $api.put(`runs/step_passed_run_case_by_run_id`, data)).data
    }

    async competeRunCase (data: ICompleteRunDto): Promise<string> {
        return (await $api.put(`runs/complete_run_cases_by_run_id`, data)).data
    }

    async deleteGroupRun (id: string): Promise<string> {
        return (await $api.delete(`runs/group_runs?group_run_id=${id}`)).data
    }

    async getFreeStreamsForGrouprun (projectId: string): Promise<string> {
        return (await $api.get(`runs/get_free_streams_for_grouprun_by_project_id`,
            { params: { project_id: projectId } })).data
    }

    async cloneRun (data: string[]): Promise<void> {
        return (await $api.post(`runs/copy_group_runs_by_ids`, data)).data
    }

    async patchSequentialOrder (groupRunId: string, cases: { group_run_case_id: string; execution_order: number }[]): Promise<void> {
        return (await $api.patch(`runs/group_runs/sequential_order?group_run_id=${groupRunId}`, cases)).data
    }
}
