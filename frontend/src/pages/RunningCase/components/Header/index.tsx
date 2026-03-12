import { ArrowLeftOutlined, EditOutlined } from '@ant-design/icons';
import { PATHS } from '@Common/consts';
import { useThemeToken } from '@Common/hooks';
import { ITestCase } from '@Entities/test-case/models';
import { useWorkspaceStore } from '@Entities/workspace/store';
import { ControlPanel } from '@Pages/RunningCase/components/Header/components';
import { useRunningStore } from '@Pages/RunningCase/store';
import { Button, Flex, Skeleton, Typography } from 'antd';
import { Header as AntHeader } from 'antd/es/layout/layout';
import get from 'lodash/get';
import { useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

export const Header = () => {
    const token = useThemeToken()
    const currentRun = useRunningStore((state) => state.currentRun)
    const currentCase = get(currentRun, 'case', null) as ITestCase
    const navigate = useNavigate()
    const workspace = useWorkspaceStore((state) => state.workspace)
    const { state } = useLocation()
    const from = get(state, 'from', null)

    /*
     * const [searchParams] = useSearchParams()
     * const { getBackPath } = useBackPath()
     */

    useEffect(() => {
        const sessionFrom = sessionStorage.getItem('fromPathRunningCase')

        if (!sessionFrom && from) {
            sessionStorage.setItem('fromPathRunningCase', from)
        }

        return () => {
            sessionStorage.removeItem('fromPathRunningCase')
        }
    }, [])

    const handleBack = () => {
        const sessionFrom = sessionStorage.getItem('fromPathRunningCase')

        if (sessionFrom) {
            navigate(sessionFrom)

            return
        } 

        if (workspace?.workspace_id) {
            navigate(-1)
        } else {
            navigate(PATHS.REPOSITORY.ABSOLUTE(currentCase.project_id!))
        }

        return
    }

    const handleEditCase = () => {
        const projectId = currentCase?.project_id

        if (projectId) {
            navigate(PATHS.REPOSITORY.EDIT_CASE.ABSOLUTE(projectId, currentCase.case_id))
        }
    }

    return (
        <AntHeader
            style={ {
                position: 'sticky',
                top: 0,
                zIndex: 1,
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                borderBottom: `1px solid ${token.colorBorder}`
            } }
        >
            <Flex align="center" gap={ 8 }>
                <Button icon={ <ArrowLeftOutlined/> } onClick={ handleBack } type="text"/>
                <Flex vertical>
                    {currentCase ? (
                        <>
                            <Flex align={ 'center' } gap={ 4 }>
                                <Typography.Title
                                    level={ 4 }>{currentCase.name}
                                </Typography.Title>
                                <Button icon={ <EditOutlined/> } onClick={ handleEditCase } type={ 'text' }/>
                            </Flex>
                            <Typography.Text style={ { fontSize: '12px', color: token.colorTextDescription } }>
                                {currentCase.case_id}
                            </Typography.Text>
                        </>
                    ) : <Skeleton.Input/>
                    }
                </Flex>
            </Flex>

            <ControlPanel/>
        </AntHeader>
    )
}
