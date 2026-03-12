import Icon from '@ant-design/icons';
import PlayArrowFilled from '@Assets/icons/play_arrow_filled.svg?react'
import { asyncHandler } from '@Common/utils';
import { useStartGroupRun } from '@Entities/runs/queries';
import { Button } from 'antd';
import { ReactNode, useEffect } from 'react';
import { useTranslation } from 'react-i18next';

const PlayIcon = <Icon component={ () => <PlayArrowFilled/> }/>

interface IProps {
    groupId: string
    runIds: string[]
    renderButton?: ({ onClick, label }: { onClick: () => void, label: string }) => ReactNode
    onSuccess?: (ids: string[]) => void
    setLoading?: (value: boolean) => void
}

export const StartManual = ({ runIds, groupId, renderButton, onSuccess, setLoading }: IProps) => {
    const { t } = useTranslation()

    const { mutateAsync, isPending } = useStartGroupRun()
    const label = t('caseTypes.manual')

    useEffect(() => {
        if (setLoading) {
            setLoading(isPending)
        }
    }, [isPending]);

    const handleClick = async () => {
        await asyncHandler(mutateAsync.bind(null, {
            group_run_id: groupId,
            runIds: runIds,
            run_manual: true
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
