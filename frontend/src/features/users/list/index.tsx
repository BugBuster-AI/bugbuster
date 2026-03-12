import { PAGINATION } from '@Common/consts';
import { AsyncData } from '@Components/AsyncData';
import { useAuthStore } from '@Entities/auth/store/auth.store.ts';
import { UsersTable } from '@Entities/users/components/UsersTable';
import { EUserRole, IUsersList } from '@Entities/users/models';
import { userQueries } from '@Entities/users/queries';
import { useWorkspaceStore } from '@Entities/workspace/store';
import { DeleteUser } from '@Features/users/delete';
import { EditUser } from '@Features/users/edit';
import { UserProjectsView } from '@Features/users/user-projects-view';
import { Flex } from 'antd';
import { useState } from 'react';

export const UsersList = () => {
    const [page, setPage] = useState(PAGINATION.PAGE)
    const [pageSize, setPageSize] = useState(PAGINATION.PAGE_SIZE)
    const setLimits = useWorkspaceStore((state) => state.setLimits)
    const [data, setData] = useState<IUsersList | undefined>(undefined)

    const user = useAuthStore((state) => state.user)

    const handleChangePage = (page: number, pageSize: number) => {
        setPage(page)
        setPageSize(pageSize)
    }

    const handleLoad = (data: IUsersList) => {
        setData(data)
        setLimits(data?.workspace_limits)
    }

    return (
        <AsyncData<IUsersList>
            dataKey={ 'items' }
            onDataLoad={ handleLoad }
            //@ts-ignore
            queryOptions={ userQueries.list({
                limit: pageSize,
                offset: (page - 1) * pageSize,
                workspaceId: user?.active_workspace_id
            }) }
        >
            <UsersTable
                pagination={ {
                    pageSize,
                    defaultCurrent: page,
                    onChange: handleChangePage,
                    pageSizeOptions: PAGINATION.PAGE_SIZE_OPTIONS,
                    total: data?.total,
                    showSizeChanger: true
                } }
                renderAction={ user?.role === EUserRole.ADMIN ? (record) => (
                    <Flex justify={ 'end' }>
                        <EditUser user={ record }/>
                        <DeleteUser { ...record } />
                    </Flex>
                ) : undefined }
                renderProject={ (record) => <UserProjectsView record={ record }/> }
            />
        </AsyncData>
    )
}
