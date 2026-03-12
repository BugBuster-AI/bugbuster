import { ConfirmButton } from '@Common/components';
import { asyncHandler } from '@Common/utils';
import { RunApi } from '@Entities/runs/api';
import { Button, ButtonProps, Typography } from 'antd';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

const runsApi = RunApi.getInstance()

interface IProps {
    groupId: string
    disabled?: boolean
    buttonProps?: ButtonProps
}

export const StopGroupRun = ({ groupId, disabled, buttonProps }: IProps) => {
    const { t } = useTranslation()
    const [loading, setLoading] = useState(false)

    const handleStopRun = async () => {
        if (disabled) return
        setLoading(true)
        await asyncHandler(runsApi.stopGroupedRun.bind(null, groupId), {
            successMessage: t('test_case_run.stopped')
        })
        setLoading(false)
    }

    return <ConfirmButton
        modalProps={ {
            okButtonProps: {
                color: 'danger',
                variant: 'solid'
            },
            centered: true,
            destroyOnClose: true,
            okText: t('group_run.stop.ok'),
            onOk: handleStopRun,
            title: t('group_run.stop.title')
        } }
        renderButton={ ({ onClick }) => (
            <Button
                disabled={ disabled }
                loading={ loading }
                onClick={ onClick }
                type={ 'primary' }
                { ...buttonProps }
            >
                {t('grouped_run.buttons.stop')}
            </Button>
        ) }
        closeAfterOk
    >
        <Typography.Text>
            {t('group_run.stop.body')}
        </Typography.Text>
    </ConfirmButton>
}
