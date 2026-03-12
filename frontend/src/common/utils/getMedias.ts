import { ToolsApi } from '@Common/api';
import { asyncHandler } from '@Common/utils/async.ts';
import { IMedia } from '@Entities/runs/models';
import size from 'lodash/size';

const toolsApi = ToolsApi.getInstance()

export const getMedias = async (files?: File[]): Promise<IMedia[] | undefined> => {
    let medias: IMedia[] | null | undefined = []
    let error = undefined

    if (!files) return undefined

    if (size(files)) {
        const formData = new FormData();

        files?.forEach((file) => {
            formData.append('files', file);
        });

        medias = await asyncHandler(toolsApi.uploadFiles.bind(null, formData), {
            successMessage: null,
            errorMessage: null,
            onSuccess: (data) => medias = data,
            onError: (_, err) => {
                throw (err)
            }
        })

        if (Boolean(error)) {
            throw new Error(error)
        }
    }

    return medias || undefined
}
