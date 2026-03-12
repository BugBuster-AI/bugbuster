import { CreateRunForm, SelectCaseForm } from '@Features/runs/create-run-from-cases/components';
import { IFormRef } from '@Features/runs/create-run-from-cases/components/CreateForm';
import { useCreateRunStore } from '@Features/runs/create-run-from-cases/store';
import { Button, Modal } from 'antd';
import { ReactNode, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

interface IProps {
    renderButton?: ({ onClick, label }: { onClick: () => void, label: string }) => ReactNode
}

export const CreateRunFromCases = ({ renderButton }: IProps) => {
    const step = useCreateRunStore((state) => state.step)
    const setStep = useCreateRunStore((state) => state.setStep)
    const saveTempValues = useCreateRunStore((state) => state.saveTempValues)
    const clear = useCreateRunStore((state) => state.clear)
    const isEdit = useCreateRunStore((state) => state.isEdit)


    const [loading, setLoading] = useState(false)
    const { t } = useTranslation();

    const modalTitle = isEdit ? t('edit_group_run.title') : t('create_run.modal.title')

    const formRef = useRef<IFormRef>(null)

    const saveValues = () => {
        saveTempValues()
        setStep(1)
    }

    const handleSubmit = async () => {
        setLoading(true)
        try {

            await formRef?.current?.submit()
        } catch (e) {
            console.error(e)
        } finally {
            setLoading(false)
        }

    }

    const handleClose = () => {
        clear()
        setStep(undefined)
    }

    const handleStartClick = () => {
        if (!step) {
            setStep(1)
        }
    }

    return (
        <>
            {renderButton
                ? renderButton({ onClick: handleStartClick, label: t('run.button_create') }) :
                <Button
                    color="primary"
                    onClick={ handleStartClick }
                    variant="solid"
                >
                    {t('run.button_create')}
                </Button>
            }
            <Modal
                animation={ false }
                modalRender={ (modal) => <div onKeyDown={ (e) => e.stopPropagation() }>{modal}</div> }
                okButtonProps={ {
                    loading
                } }
                onCancel={ handleClose }
                onOk={ handleSubmit }
                open={ step !== undefined }
                title={ modalTitle }
                width={ 720 }
                centered
                destroyOnClose
            >
                <CreateRunForm ref={ formRef } afterSubmit={ handleClose }/>
            </Modal>
            <Modal
                cancelText={ t('create_run.cancel_select_cases') }
                okText={ t('create_run.done_select_cases') }
                onCancel={ setStep.bind(null, 1) }
                onOk={ saveValues }
                open={ Number(step) === 2 }
                title={ t('create_run.modal.title_select') }
                width={ '90%' }
                centered
                destroyOnClose
            >
                <SelectCaseForm/>
            </Modal>
        </>
    )

}
