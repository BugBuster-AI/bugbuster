import { AsyncData } from '@Components/AsyncData';
import { DebouncedSearch } from '@Components/DebouncedSearch';
import { useAuthStore } from '@Entities/auth/store/auth.store';
import TableProjects from '@Entities/project/components/Table';
import { projectQueries } from '@Entities/project/queries';
import { useStreamStore } from '@Entities/stream/store';
import { CreateProject } from '@Features/project/create-project';
import { DeleteProject } from '@Features/project/delete-project';
import { EditProject } from '@Features/project/edit-project';
import { ViewWorkspaceStreams } from '@Features/stream/view-workspace-streams';
import { adaptProjectsData } from '@Pages/Main/helper.ts';
import { Col, Flex, Row, Space, theme } from 'antd';
import { AxiosError } from 'axios';
import { ReactElement, useState } from 'react';

const { useToken } = theme

const MainPage = (): ReactElement => {
    const { token } = useToken()
    const user = useAuthStore((state) => state.user)
    const streams = useStreamStore((state) => state.streams)
    const [error, setError] = useState<AxiosError | null>()
    const [, setLoading] = useState(false)
    const [searchValue, setSearchValue] = useState('')

    return (
        <Space
            direction="vertical"
            size="large"
            style={ {
                width: '100%',
                borderLeft: `${token.lineWidth}px solid ${token.colorBorder}`,
                padding: `${token.paddingContentVerticalLG}px ${token.paddingXL}px`
            } }>
            <Row>
                <Col flex={ 'auto' }>
                    <Flex gap={ 8 }>
                        <CreateProject disabled={ error?.status === 403 }/>
                        <DebouncedSearch onChange={ setSearchValue }/>
                    </Flex>
                </Col>
                <Col flex={ 'none' }>
                    <ViewWorkspaceStreams/>
                </Col>
            </Row>

            <AsyncData
                onError={ (error) => setError(error as AxiosError) }
                onLoading={ setLoading }
                queryOptions={ { ...projectQueries.list(user?.active_workspace_id, { search: searchValue }) } }
                transformData=
                    { (data) => adaptProjectsData({ streams: streams?.project_statistics, projects: data }) }
            >
                <TableProjects
                    DeleteButton={ (record) => <DeleteProject { ...record }/> }
                    EditButton={ (record) => <EditProject initialValues={ record }/> }
                />
            </AsyncData>
        </Space>
    )
}

export default MainPage;
