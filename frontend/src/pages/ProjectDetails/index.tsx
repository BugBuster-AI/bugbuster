import { SideBar } from '@Common/layouts';
import { projectQueries } from '@Entities/project/queries';
import { projectKeys } from '@Entities/project/queries/query-keys.ts';
import { useProjectStore } from '@Entities/project/store';
import { ProjectSearch } from '@Pages/ProjectDetails/components';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Layout, theme } from 'antd';
import Sider from 'antd/es/layout/Sider';
import { ReactElement, useEffect } from 'react';
import { Outlet, useParams } from 'react-router-dom';

const { useToken } = theme

const ProjectPage = (): ReactElement => {
    const { token } = useToken();
    const { id } = useParams()
    const { data } = useQuery(projectQueries.byId(id!!))
    const setProject = useProjectStore.use.setProject()
    const queryClient = useQueryClient()

    useEffect(() => {
        if (data) {
            setProject(data)
            queryClient.setQueryData([projectKeys.projectId], data.project_id)
        }
    }, [data]);

    useEffect(() => {
        return () => {
            setProject(undefined)
        }
    }, []);

    return (
        <Layout hasSider={ true } style={ { height: '100%', background: token.colorBgBase } }>
            <Sider
                style={ {
                    height: '100%',
                    backgroundColor: `${token.colorFillQuaternary}`,
                    padding: `${token.paddingContentVerticalLG}px ${token.paddingContentHorizontal}px`
                } }
                theme="light"
                width={ 256 }
            >
                <SideBar nameSlot={ <ProjectSearch/> }/>
            </Sider>

            <Layout style={ { background: token.colorBgBase, overflow: 'auto' } }>
                <Outlet/>
            </Layout>
        </Layout>
    )
}

export default ProjectPage
