import Icon from '@ant-design/icons';
import PlayArrowFilled from '@Assets/icons/play_arrow_filled.svg?react'
import { asyncHandler } from '@Common/utils';
import { useStartGroupRun } from '@Entities/runs/queries';
import { useStreamsLimitModal } from '@Pages/Runs/entities/Details/components/StreamsLimitModal';
import { Button } from 'antd';
import { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

const PlayIcon = <Icon component={ () => <PlayArrowFilled/> }/>

interface IProps {
    groupId: string
    runIds: string[]
    renderButton?: ({ onClick, label }: { onClick: () => void, label: string }) => ReactNode
    onSuccess?: (ids: string[]) => void
    onStart?: () => void
    available?: boolean | null
}

export const StartAutomated = ({ runIds, available, groupId, renderButton, onSuccess, onStart }: IProps) => {
    const { t } = useTranslation()

    const label = t('caseTypes.automated')
    const { mutateAsync, isPending } = useStartGroupRun()
    const { open } = useStreamsLimitModal()
    const handleClick = async () => {
        if (available === null) {
            return
        }

        if (available === false) {
            open()

            return
        }
        onStart && onStart()
        await asyncHandler(mutateAsync.bind(null, {
            group_run_id: groupId,
            runIds: runIds,
            run_automated: true
        }), {
            onSuccess: (data) => {
                onSuccess && onSuccess(data.run_ids)
            }
        })
    }

    if (renderButton) {
        return renderButton({ onClick: handleClick, label })
    }

    return (
        <Button icon={ PlayIcon } loading={ isPending } onClick={ handleClick }>
            {label}
        </Button>
    )
}
