import { asyncHandler } from '@Common/utils';
import { useStartGroupRun } from '@Entities/runs/queries/mutations';
import { useStreamsLimitModal } from '@Pages/Runs/entities/Details/components/StreamsLimitModal';
import { Button, ButtonProps } from 'antd';
import { useTranslation } from 'react-i18next';

interface IProps extends ButtonProps {
    group_id: string
    available?: boolean | null
}

export const StartGroupRun = ({ group_id, available, ...props }: IProps) => {
    const { t } = useTranslation()
    const { open } = useStreamsLimitModal()

    const { mutateAsync, isPending } = useStartGroupRun()

    const handleClick = async () => {
        if (available === null) {
            return
        }

        if (available === false) {
            open()

            return
        }

        if (!group_id) {
            return
        }

        await asyncHandler(mutateAsync.bind(null, { group_run_id: group_id }))
    }

    return (
        <Button loading={ isPending } onClick={ handleClick } type={ 'primary' } { ...props }>
            {t('grouped_run.buttons.run')}
        </Button>
    )
}
