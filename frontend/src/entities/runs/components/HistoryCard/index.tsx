import { ClockCircleOutlined, LinkOutlined } from '@ant-design/icons';
import { StatusBadge } from '@Common/components';
import { PATHS } from '@Common/consts';
import { formatSeconds } from '@Common/utils/formatSeconds.ts';
import { VideoLoader } from '@Entities/runs/components/VideoLoader';
import { IRunById } from '@Entities/runs/models';
import { getRunInfo } from '@Entities/runs/utils/runInfo.ts';
import { TestTypeIcon } from '@Entities/test-case/components/Icons';
import { RunStepsView } from '@Entities/test-case/components/StepsView/RunStepsView.tsx';
import { useLocalRunStepsData } from '@Entities/test-case/hooks/useLocalStepData.ts';
import { Button, Collapse, CollapseProps, Flex, Typography } from 'antd';
import dayjs from 'dayjs'
import { MouseEvent, ReactElement, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

interface IProps extends IRunById {

}

export const RunHistoryCard = (run: IProps): ReactElement => {
    const { run_id, status, created_at, show_trace, complete_time } = run || {}
    const { t } = useTranslation()

    const openVideo = () => {
        if (!run.video) return

        window.open(run.video.url, '_blank')
    }

    const handleTrace = (e: MouseEvent) => {
        e.stopPropagation()
        if (!show_trace) return

        window.open(show_trace, '_blank')
    }
    const navigate = useNavigate()
    const handleOpenCase = () => {
        const fromLocation = window.location.pathname + window.location.search

        if (run) {
            navigate(`${PATHS.RUNNING.ABSOLUTE(run.run_id!)}`, {
                state: {
                    from: fromLocation
                }
            })
        }
    }

    const { steps: localSteps, attachments } = useLocalRunStepsData({ run })


    const { isInFinish, isGeneratingVideo } = useMemo(() => getRunInfo(run), [run]) || {}
    const items: CollapseProps['items'] = [
        {
            headerClass: 'header-accordion',
            key: run_id,
            label: (
                <Flex align={ 'center' } justify={ 'space-between' }>
                    <Flex align={ 'center' } gap={ 8 }>
                        <TestTypeIcon type={ run?.case?.case_type_in_run }/>
                        <Typography.Text style={ { width: '150px' } }>
                            {dayjs(created_at).format('DD.MM.YYYY HH:mm:ss')}
                        </Typography.Text>
                        <StatusBadge status={ status }/>
                    </Flex>
                    <Flex align={ 'center' } gap={ 8 }>
                        <Typography.Text style={ { marginRight: '24px' } }>
                            <ClockCircleOutlined style={ { marginRight: '8px' } }/>
                            {formatSeconds(Number(complete_time || 0), t)}
                        </Typography.Text>

                        <Button
                            disabled={ !show_trace }
                            onClick={ handleTrace }
                            style={ { background: 'transparent' } }
                        >
                            {t('running_page.buttons.trace')}
                        </Button>

                        <Button
                            icon={ <LinkOutlined/> }
                            onClick={ handleOpenCase }
                            style={ { background: 'transparent' } }/>

                    </Flex>
                </Flex>
            ),
            children: (
                <Flex className={ 'history-card-item ' } gap={ 8 } vertical>
                    <RunStepsView
                        attachments={ attachments }
                        grouping={ false }
                        status={ run?.status }
                        steps={ localSteps }
                        summary={ run?.run_summary }
                    />

                    {isGeneratingVideo && <VideoLoader/>}
                    {isInFinish && (
                        <Button
                            onClick={ openVideo }
                            style={ {
                                textDecoration: 'underline', width: 'fit-content', height: 'fit-content'
                            } }
                            type={ 'link' }
                        >
                            {t('runs_history.view_video')}
                        </Button>
                    )}
                </Flex>
            )
        }
    ]

    return <Collapse items={ items } style={ { alignItems: 'center' } }/>
}
