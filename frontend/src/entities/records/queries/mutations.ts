import { RecordsApi } from '@Entities/records/api';
import { IGenerateHappypassPayload } from '@Entities/records/models/generate-happypass.ts';
import { recordQueries } from '@Entities/records/queries';
import { recordsKeys } from '@Entities/records/queries/query-keys';
import { useMutation, useQueryClient } from '@tanstack/react-query';

const recordsApi = RecordsApi.getInstance()

export const useDeleteHappypass = (projectId: string) => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationKey: [recordsKeys.delete],
        mutationFn: (id: string) => recordsApi.deleteHappypass(id),
        onSuccess: () => queryClient.invalidateQueries(recordQueries.list({ projectId }))
    })
}

export const useGenerateAutosop = (projectId: string = '') => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (data: IGenerateHappypassPayload) => recordsApi.generateHappypass(data),
        onSuccess: (_, data) => {
            queryClient.invalidateQueries(recordQueries.showFull({
                happy_pass_id: data.happy_pass_id,
                project_id: projectId!
            }))
        }
    })
}
