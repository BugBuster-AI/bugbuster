import { DeleteOutlined } from '@ant-design/icons';
import { ConfirmButton } from '@Common/components';
import { asyncHandler } from '@Common/utils';
import { IProjectListItem } from '@Entities/project';
import { useDeleteProject } from '@Entities/project/queries/mutations';
import { Typography } from 'antd';
import { ReactElement } from 'react';
import { useTranslation } from 'react-i18next';

type Props = Pick<IProjectListItem, 'project_id' | 'name'>

export const DeleteProject = ({ project_id, name }: Props): ReactElement => {
    const { mutateAsync } = useDeleteProject();
    const { t } = useTranslation();

    const handleDelete = async () => {
        await asyncHandler(mutateAsync.bind(null, project_id), {
            successMessage: t('messages.success.delete.projects', { name }),
            errorMessage: t('messages.error.delete.projects', { name }),
        })
    };

    return (
        <ConfirmButton
            icon={ <DeleteOutlined /> }
            modalProps={ {
                centered: true,
                title: t('project.buttons.delete'),
                onOk: handleDelete,
                okText: t('project.buttons.delete'),
                cancelText: t('project.buttons.cancel'),
            } }
            closeAfterOk
        >
            <Typography.Text>
                { t('confirm.delete.projects', { project_name: name }) }
            </Typography.Text>
        </ConfirmButton>
    );
};
