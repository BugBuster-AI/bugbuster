import { ReloadOutlined } from '@ant-design/icons';
import { EStatusIndicator, StatusIndicator } from '@Common/components';
import { useThemeToken } from '@Common/hooks';
import { asyncHandler } from '@Common/utils';
import { useProjectStore } from '@Entities/project/store';
import { useGenerateAutosop } from '@Entities/records/queries/mutations.ts';
import { useShowRecordStore } from '@Features/records/show-record/store';
import { Button, Flex, message, Typography } from 'antd';
import { useTranslation } from 'react-i18next';

export const ErrorCard = () => {
    const { t } = useTranslation()
    const token = useThemeToken()
    const project = useProjectStore((state) => state.currentProject)

    const { mutateAsync, isPending } = useGenerateAutosop(project?.project_id!)
    const { record } = useShowRecordStore()

    const handleGenerateAutosop = async () => {
        if (record?.happy_pass_id) {
            await asyncHandler(mutateAsync.bind(null, {
                happy_pass_id: record?.happy_pass_id
            }))
        } else {
            message.error('No record id!')
        }
    }

    return (
        <Flex gap={ 8 } vertical>
            <Flex
                align={ 'flex-start' }
                gap={ 16 }
                style={ {
                    width: '100%',
                    border: `1px solid ${token.colorErrorBorder}`,
                    borderRadius: '6px',
                    padding: '20px 24px',
                    backgroundColor: token.colorErrorBg
                } }
            >
                <StatusIndicator status={ EStatusIndicator.ERROR }/>
                <Flex gap={ 4 } vertical>
                    <Typography.Text>{t('records.error.title')}</Typography.Text>
                    <Typography.Text>{t('records.error.subtitle')}</Typography.Text>
                </Flex>
            </Flex>

            <Button
                icon={ <ReloadOutlined/> }
                loading={ isPending }
                onClick={ handleGenerateAutosop }
                style={ { width: 'fit-content' } }
                variant={ 'text' }>
                {t('records.error.try_again')}
            </Button>
        </Flex>
    )
}
