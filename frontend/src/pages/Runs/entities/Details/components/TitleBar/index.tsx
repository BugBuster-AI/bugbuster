import { LoadingOutlined, MoreOutlined } from '@ant-design/icons';
import { TextWithIcon } from '@Common/components';
import { formatSeconds } from '@Common/utils/formatSeconds.ts';
import { ProgressStats } from '@Entities/runs/components/Table/components';
import { ERunStatus } from '@Entities/runs/models';
import { useStreamStore } from '@Entities/stream/store';
import { CreateRunFromCases } from '@Features/runs/create-run-from-cases';
import { useCreateRunStore } from '@Features/runs/create-run-from-cases/store';
import { adaptRunData, transformCases } from '@Features/runs/list/helper.ts';
import { StartGroupRun } from '@Features/runs/start-group-run';
import { StopGroupRun } from '@Features/runs/stop-group-run';
import { useGroupedRunStore } from '@Pages/Runs/entities/Details/store';
import { Button, Dropdown, Flex, MenuProps, Skeleton, Typography } from 'antd';
import head from 'lodash/head';
import includes from 'lodash/includes';
import { useTranslation } from 'react-i18next';


export const TitleBar = () => {
    const itemRun = useGroupedRunStore((state) => state.runItem)
    const isError = useGroupedRunStore((state) => state.isError)
    const isLoading = useGroupedRunStore((state) => state.isLoading)
    const setSelectedCases = useCreateRunStore((state) => state.setCaseId)
    const setInitialData = useCreateRunStore((state) => state.setInitialData)
    const setEdit = useCreateRunStore((state) => state.setIsEdit)
    const streams = useStreamStore((state) => state.streams)
    const runStreams = useGroupedRunStore((state) => state.streams)
    const isAvailableStreams = runStreams && runStreams?.total_streams > 0
    const { t } = useTranslation()

    const menu: MenuProps = {
        items: [
            {
                key: 'settings',
                // label: t('grouped_run.buttons.settings')
                label: <CreateRunFromCases
                    renderButton={ ({ onClick }) => {
                        const handleClick = () => {


                            const transformedData = transformCases(itemRun)
                            const adaptedData =
                                adaptRunData({ items: itemRun ? [itemRun] : [] }, streams?.group_run_statistics)
                            const headData = head(adaptedData)

                            setEdit()
                            setSelectedCases(transformedData)
                            setInitialData(headData)
                            onClick()
                        }

                        return (
                            <Typography.Text
                                key={ 'runs-list-dropdown-edit' }
                                onClick={ handleClick }
                                style={ { display: 'block', textAlign: 'left', width: 100 } }>
                                {t('group_run.list_dropdown.edit')}
                            </Typography.Text>
                        )
                    } }
                />
            }
        ]
    }

    if (isLoading && !itemRun) return (
        <Flex align={ 'center' } gap={ 24 }>
            <Skeleton.Input style={ { width: 80 } }/>
            <Skeleton.Input style={ { width: 300 } }/>
            <Skeleton.Input style={ { width: 165 } }/>
        </Flex>
    )

    if (isError) return null

    if (!itemRun) return null

    return (
        <Flex align={ 'center' } gap={ 24 }>
            <TextWithIcon
                icon={ itemRun.status === ERunStatus.IN_PROGRESS ? <LoadingOutlined
                    spin/> : undefined }>
                {formatSeconds(Number(itemRun.complete_time || 0), t)}
            </TextWithIcon>

            <ProgressStats
                stats={ itemRun.stats }
                style={ { width: 300 } }
            />

            <Flex align={ 'center' } gap={ 8 }>
                <StartGroupRun
                    available={ isAvailableStreams }
                    disabled={ itemRun.status !== ERunStatus.UNTESTED }
                    group_id={ itemRun.group_run_id }/>
                <StopGroupRun
                    disabled={ !includes([ERunStatus.IN_QUEUE, ERunStatus.IN_PROGRESS], itemRun.status) }
                    groupId={ itemRun.group_run_id }
                />
                <Dropdown menu={ menu } trigger={ ['click'] }>
                    <Button
                        icon={ <MoreOutlined style={ { transform: 'rotate(90deg)' } }/> }
                        type={ 'text' }
                    />
                </Dropdown>
            </Flex>
        </Flex>
    )
}
