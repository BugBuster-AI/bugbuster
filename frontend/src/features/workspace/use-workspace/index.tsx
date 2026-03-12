import { useAuthStore } from '@Entities/auth/store/auth.store';
import { workspaceQueries } from '@Entities/workspace/queries';
import { useWorkspaceStore } from '@Entities/workspace/store';
import { useQuery } from '@tanstack/react-query';
import head from 'lodash/head';
import { useEffect } from 'react';

export const useWorkspace = () => {
    const user = useAuthStore((state) => state.user)
    const getUser = useAuthStore((state) => state.getUser)
    const setWorkspace = useWorkspaceStore((state) => state.setWorkspace)
    const workspaceId = user?.active_workspace_id

    const workspaceQueryData = useQuery({ ...workspaceQueries.byId(workspaceId!), enabled: !!workspaceId })

    const data = workspaceQueryData.data

    const currentWorkspace = data ? head(data) : null

    useEffect(() => {
        if (!user) {
            getUser()

            return
        }
        if (data && user) {
            const currentWorkspace = head(data)

            if (currentWorkspace) {
                setWorkspace(currentWorkspace)
            }
        }
    }, [data, user]);

    return { ...workspaceQueryData, data: currentWorkspace }
}
