import { EditOutlined } from '@ant-design/icons';
import { useThemeToken } from '@Common/hooks';
import { IModalRef, ModalButton } from '@Components/ModalButton';
import { IUserListItem } from '@Entities/users/models';
import { Button, Flex, Tag, Typography } from 'antd';
import head from 'lodash/head';
import map from 'lodash/map';
import size from 'lodash/size';
import { useRef } from 'react';
import { useTranslation } from 'react-i18next';

interface IProps {
    record?: IUserListItem
}

export const UserProjectsView = ({ record }: IProps) => {
    const { t } = useTranslation()
    const ref = useRef<IModalRef>(null)
    const token = useThemeToken()
    const projects = record?.projects
    const projectsSize = size(projects)
    const name = (record?.first_name || record?.last_name) ? `${record?.first_name} ${record?.last_name}` : ''
    const project = head(projects)

    return (
        <ModalButton
            ref={ ref }
            buttonProps={ { variant: 'filled', type: 'text' } }
            icon={ <EditOutlined/> }
            modalProps={ {
                width: 420,
                title: t('users.projects_modal.title'),
                centered: true,
                destroyOnClose: true,
                footer: <Flex justify={ 'end' }>
                    <Button
                        onClick={ () => ref.current?.close() }
                        type={ 'primary' }>{t('common.ok')}
                    </Button>
                </Flex>
            } }
            renderButton={ ({ onClick }) => (
                <Flex onClick={ onClick } style={ { cursor: 'pointer' } }>
                    <Tag
                        color={ 'default' }
                        style={ { cursor: 'pointer' } }>
                        {project?.project_name}
                    </Tag>
                    {projectsSize > 1 &&
                        <span style={ { color: token.colorLink } }>+{projectsSize - 1}</span>
                    }
                </Flex>
            ) }
        >
            <Flex gap={ 16 } style={ { paddingBlock: 16 } } vertical>
                <Typography.Text>{t('users.projects_modal.body', { name })}</Typography.Text>
                <Flex vertical>
                    {map(projects, (item) => (
                        <Flex style={ { borderBottom: `1px solid ${token.colorSplit}`, paddingBlock: 12 } }>
                            <Typography.Text style={ { flex: 1 } }>{item.project_name}</Typography.Text>
                        </Flex>
                    ))}
                </Flex>
            </Flex>
        </ModalButton>
    )
}
