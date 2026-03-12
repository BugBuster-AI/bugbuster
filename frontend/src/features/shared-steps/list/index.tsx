import { PATHS } from '@Common/consts';
import { asyncHandler } from '@Common/utils';
import { SharedStepsTable } from '@Entities/shared-steps';
import { ISharedStep } from '@Entities/shared-steps/models';
import { sharedStepsQueries } from '@Entities/shared-steps/queries';
import { useDeleteSharedStep } from '@Entities/shared-steps/queries/mutations';
import { useQuery } from '@tanstack/react-query';
import { Button, Flex, message, Modal } from 'antd';
import map from 'lodash/map';
import { ReactElement, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate, useParams } from 'react-router-dom';

enum EHTTPStatus {
    FAILED = 'FAILED',
    SUCCESS = 'OK'
}

interface IProps {
    search?: string
}

export const SharedStepsList = ({ search }: IProps): ReactElement => {
    const { id } = useParams()
    const { data, isLoading } = useQuery({
        ...sharedStepsQueries.list({ project_id: id!, search }),
        enabled: !!id
    })

    const navigate = useNavigate()
    const { mutateAsync: deleteStep } = useDeleteSharedStep()
    const { t } = useTranslation()

    const [isModalVisible, setIsModalVisible] = useState(false);
    const [modalContent, setModalContent] = useState<React.ReactNode>(null);
    const [modalTitle, setModalTitle] = useState('');
    const [showOkButton, setShowOkButton] = useState(true);
    const [isDeleting, setIsDeleting] = useState(false);
    const [recordToDelete, setRecordToDelete] = useState<ISharedStep | null>(null);

    const handleDelete = (record: ISharedStep) => {
        setRecordToDelete(record);
        setModalTitle(t('sharedStepsPage.delete.title'));
        setModalContent(<div>{t('sharedStepsPage.delete.content', { name: record.name })}</div>);
        setShowOkButton(true);
        setIsModalVisible(true);
        setIsDeleting(false)
    };

    const handleCancel = () => {
        setIsModalVisible(false);
        setIsDeleting(false);
    };

    const confirmDelete = async () => {
        if (!recordToDelete) return;

        setIsDeleting(true);
        await asyncHandler(deleteStep.bind(null, { id: recordToDelete.shared_steps_id }), {
            successMessage: null,
            errorMessage: null,
            onSuccess: (response: any) => {
                try {
                    const isError = response?.status === EHTTPStatus.FAILED
                    const caseLinks = response?.case_links

                    if (isError) {
                        const baseMsg = t('sharedStepsPage.delete.warn')
                        const messageText = caseLinks
                            ? <>
                                {baseMsg}<br/>
                                <Flex gap={ 4 } style={ { marginTop: 4 } } vertical>
                                    {map(caseLinks, (item) => <Link
                                        to={ `${PATHS.REPOSITORY.ABSOLUTE(id!)}?caseId=${item.case_id}` }>
                                        {item.case_name}
                                    </Link>)}
                                </Flex>
                            </>
                            : 'Error';

                        setModalContent(messageText);
                        setShowOkButton(false);
                        setIsDeleting(false);
                        throw new Error('error deleting shared step with links');
                    } else {
                        message.success(t('common.success'))
                        setIsModalVisible(false);
                    }
                } catch (e) {
                    console.error('error deleting shared step');
                    throw e;
                }
            },
        });
        // Если asyncHandler не поймал ошибку, но onSuccess вернул isError=false
        if (!isModalVisible) { // onSuccess мог уже закрыть модалку
            setIsDeleting(false);
        }
    };

    const handleEdit = (record: ISharedStep) => {
        navigate(`edit/${record.shared_steps_id}`)
    }

    return (
        <>
            <SharedStepsTable
                data={ data || [] }
                loading={ isLoading }
                onDelete={ handleDelete }
                onEdit={ handleEdit }
                props={ {
                    rowClassName: 'clickable-row',
                    onRow: (record) => ({
                        onClick: () => handleEdit(record)
                    })
                } }
            />
            <Modal
                footer={ [
                    <Button key="back" disabled={ isDeleting } onClick={ handleCancel }>
                        {showOkButton ? t('sharedStepsPage.delete.cancel') : t('common.close')}
                    </Button>,
                    ...(showOkButton ? [<Button
                        key="submit"
                        loading={ isDeleting }
                        onClick={ confirmDelete }
                        type="primary"
                        danger
                    >
                        {t('sharedStepsPage.delete.ok')}
                    </Button>] : [])
                ] }
                maskClosable={ !isDeleting }
                onCancel={ handleCancel }
                open={ isModalVisible }
                title={ modalTitle }
                width={ 412 }
                centered
                destroyOnClose
            >
                {modalContent}
            </Modal>
        </>
    )
}
