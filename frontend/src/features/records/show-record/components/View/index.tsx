import { PATHS } from '@Common/consts';
import { useProjectStore } from '@Entities/project/store';
import { useShowRecordStore } from '@Features/records/show-record/store';
import { Flex, Modal, Skeleton, Typography } from 'antd';
import dayjs from 'dayjs'
import { ReactNode, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useSearchParams } from 'react-router-dom';

interface IProps {
    children?: ReactNode
}

export const ShowView = ({ children }: IProps) => {
    const { t } = useTranslation()
    const [s, setSearchParams] = useSearchParams()
    const project = useProjectStore((state) => state.currentProject)

    const record = useShowRecordStore((state) => state.record)
    const loading = useShowRecordStore((state) => state.loading)
    const error = useShowRecordStore((state) => state.error)
    const open = useShowRecordStore((state) => state.open)
    const setOpen = useShowRecordStore((state) => state.setOpen)
    const clear = useShowRecordStore((state) => state.clear)

    const navigate = useNavigate()

    const handleClose = () => {
        setOpen(false)
        clear()
    }

    const handleDeleteSearchParams = () => {
        s.delete('recordId')
        setSearchParams(s)
    }

    const handleCreateCase = () => {
        const id = record?.happy_pass_id
        const projectId = project?.project_id

        if (id && projectId) {
            navigate(`${PATHS.REPOSITORY.CREATE_CASE.ABSOLUTE(projectId)}?recordId=${id}`)
        }
    }

    const title = () => {
        if (loading) return <Skeleton.Input />

        if (error) return <Typography.Text type="danger">{ error }</Typography.Text>

        if (record) return (
            <Flex vertical>
                <Typography.Text strong>{record.name}</Typography.Text>
                <Typography.Text>{dayjs(record.created_at).format('DD.MM.YYYY HH:mm:ss')}</Typography.Text>
            </Flex>
        )
    }

    useEffect(() => {
        setOpen(true)
    }, []);

    return (
        <Modal
            afterClose={ handleDeleteSearchParams }
            cancelText={ t('show_record.cancel') }
            okText={ t('show_record.create_case') }
            onCancel={ handleClose }
            onOk={ handleCreateCase }
            open={ open }
            title={ title() }
            width={ '90%' }
            centered
            destroyOnClose
        >
            {children}
        </Modal>
    )
}
