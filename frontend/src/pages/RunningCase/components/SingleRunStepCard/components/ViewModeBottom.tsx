import { EditOutlined, FieldTimeOutlined } from '@ant-design/icons';
import { useThemeToken } from '@Common/hooks';
import { EStepType } from '@Entities/test-case/components/Form/models.ts';
import { ISingleRunStepCardProps } from '@Pages/RunningCase/components/SingleRunStepCard';
import { useSingleRunStepContext } from '@Pages/RunningCase/components/SingleRunStepCard/context';
import { useRunningStore } from '@Pages/RunningCase/store';
import { Button, Flex, message, Modal, Typography } from 'antd';
import isString from 'lodash/isString';
import size from 'lodash/size';
import { CSSProperties } from 'react';
import { useTranslation } from 'react-i18next';

interface IProps extends ISingleRunStepCardProps {
    actionStyles: CSSProperties
}

export const ViewModeBottom = ({ actionStyles, onClick, actionName, time, stepInfo }: IProps) => {
    const token = useThemeToken()
    const { t } = useTranslation()
    const { changeEditing, isEditable, stepItem } = useSingleRunStepContext()
    const editingSteps = useRunningStore((state) => state.editingSteps)
    const currentRun = useRunningStore((state) => state.currentRun)

    const handleChangeToEdit = () => {
        if (!isEditable) return

        // Для expected_result шагов проверяем наличие хотя бы одного скриншота
        if (stepItem?.step_type === EStepType.RESULT) {
            const hasBefore = !!stepItem?.before?.url
            const hasAfter = !!stepItem?.after?.url

            if (!hasBefore && !hasAfter) {
                message.error(t('debug_mode.no_screenshots_error'))

                return
            }
        }

        changeEditing(true)
        onClick?.()
    }

    const handleEditClick = async (e: React.MouseEvent) => {
        e.stopPropagation()
        const hasSharedStep = currentRun?.steps?.find((item) => item?.extra?.shared_step)
        const wasEdited = (!size(editingSteps) || size(editingSteps) === 0)

        if ((hasSharedStep || stepItem?.extra?.shared_step) && wasEdited) {
            Modal.confirm({
                maskClosable: true,
                onOk: handleChangeToEdit,
                title: t('running_page.sharedStepEditModal.title'),
                centered: true,
                closable: true,
                content: t('running_page.sharedStepEditModal.description'),
                icon: null
            })

            return
        }
        handleChangeToEdit()
    }

    return <Flex
        align="center"
        gap={ 12 }
        justify="space-between"
        style={ { width: '100%' } }
    >
        {
            actionName
                ? (
                    <Typography.Text style={ { ...actionStyles } }>
                        {isString(actionName) ? actionName : actionName}
                    </Typography.Text>
                )
                : <div/>
        }

        <Flex align="center" gap={ 8 }>
            <Typography.Text 
                style={ { color: token.colorTextDescription, whiteSpace: 'nowrap' } }>
                {stepInfo}
            </Typography.Text>
            {!time === false && (
                <Typography.Text style={ { color: token.colorTextDescription, whiteSpace: 'nowrap' } }>
                    <FieldTimeOutlined style={ { color: token.colorTextDescription, marginRight: '4px' } }/>
                    {time || '0.00'}
                </Typography.Text>
            )
            }
            {isEditable && (
                <Button
                    icon={ <EditOutlined/> }
                    onClick={ handleEditClick }
                    type={ 'text' }
                    variant={ 'text' }
                />
            )}
        </Flex>
    </Flex>
}
