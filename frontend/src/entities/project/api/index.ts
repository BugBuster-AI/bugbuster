import { $api } from '@Common/api';
import { ICreateProjectPayload, IGetProjectListPayload, IProjectListItem, IProjectWithId } from '@Entities/project';

export class ProjectApi {
    private static instance: ProjectApi | null

    public static getInstance (): ProjectApi {
        if (!this.instance) {
            this.instance = new ProjectApi()

            return this.instance
        }

        return this.instance
    }

    async getList (params?: IGetProjectListPayload): Promise<IProjectListItem[]> {
        return (await $api.get('content/list_projects', { params })).data
    }

    async create (data: ICreateProjectPayload): Promise<IProjectWithId> {
        return (await $api.post('content/project', data)).data
    }

    async update (data: IProjectWithId): Promise<IProjectWithId> {
        return (await $api.put('content/project', data)).data
    }

    async delete (id: string): Promise<string> {
        return (await $api.delete(`content/project/${id}`)).data
    }

    async getById (id: string): Promise<IProjectListItem> {
        return (await $api.get(`content/get_project_by_id?project_id=${id}`)).data
    }

    async getFreeStreams (excludeId?: string): Promise<string> {
        return (await $api.get(`content/get_free_streams_for_active_workspace`,
            {
                params: { exclude_project_id: excludeId }
            }
        )).data
    }
}
