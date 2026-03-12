import { DeleteOutlined, EditOutlined, MoreOutlined, PlusOutlined } from '@ant-design/icons';
import { asyncHandler } from '@Common/utils';
import { ITreeListItem } from '@Components/TreeList/models.ts';
import { useDeleteSuite } from '@Entities/suite/queries/mutations.ts';
import { CreateSuite } from '@Features/suite/create-suite';
import { EditSuite } from '@Features/suite/edit-suite';
import { EMenuKeys, } from '@Features/suite/suite-tree/get-context-menu.tsx';
import { Dropdown, MenuProps, Typography } from 'antd';
import { MouseEvent, ReactElement, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

interface IProps {
    record?: ITreeListItem
}

export const DropDownButton = ({ record }: IProps): ReactElement => {
    const suite = record?.suite
    const { t } = useTranslation()
    const { mutateAsync } = useDeleteSuite()
    const navigate = useNavigate()
    const [open, setOpen] = useState(false)

    const items: MenuProps['items'] = [
        {
            key: EMenuKeys.EDIT_SUITE,
            style: { padding: 0 },
            label: (
                <EditSuite
                    initialValue={ {
                        name: suite?.name,
                        description: suite?.description,
                        parent_id: suite?.parent_id,
                        suite_id: suite?.suite_id
                    } }
                    renderButton={ ({ onClick }) => (
                        <Typography.Text
                            onClick={ () => {
                                onClick()
                                setOpen(false)
                            } }
                            style={ { padding: '5px 12px', width: '100%', display: 'block' } }
                        >
                            <EditOutlined style={ { marginRight: '8px' } }/>
                            {t('suite.menu.edit')}
                        </Typography.Text>
                    ) }
                />
            ),
        },
        {
            key: EMenuKeys.DELETE_SUITE,
            label: t('suite.menu.delete'),
            onClick: () => asyncHandler(mutateAsync.bind(null, suite?.suite_id!!), {
                errorMessage: t('messages.error.delete.suite', { name: suite?.name }),
                successMessage: t('messages.success.delete.suite', { name: suite?.name }),
                confirm: true,
                confirmProps: {
                    closable: true,
                    prefixCls: 'se',
                    content: t('suite.delete_content', { name: suite?.name })
                },
                t
            }),
            icon: <DeleteOutlined/>
        },
        {
            type: 'divider',
        },
        {
            key: EMenuKeys.CREATE_SUBSUITE,
            style: { padding: 0 },
            label: (
                <CreateSuite
                    initialValue={ {
                        parent_id: suite?.suite_id
                    } }
                    renderButton={ ({ onClick }) => (
                        <Typography.Text
                            onClick={ () => {
                                onClick()
                                setOpen(false)
                            } }
                            style={ { padding: '5px 12px', width: '100%', display: 'block' } }
                        >
                            <PlusOutlined style={ { marginRight: '8px' } }/>
                            {t('suite.menu.create_subsuite')}
                        </Typography.Text>
                    ) }
                />
            ),
        },
        {
            key: EMenuKeys.CREATE_CASE,
            label: 'Create case',
            icon: <PlusOutlined/>,
            onClick: () => {
                const suiteId = record?.suite?.suite_id
                const url = suiteId ? `create-case?suiteId=${suiteId}` : 'create-case'

                navigate(url)
            }
        },
    ]


    const handleClick = (e: MouseEvent) => {
        e.stopPropagation()
        setOpen(!open)
    }

    const handleOpenChange = () => {
        setOpen(false);
    };

    const onDropdownClick = (e: MouseEvent) => {
        e.stopPropagation()
    }

    return (
        <Dropdown
            dropdownRender={ (originNode) => <div onClick={ onDropdownClick }>{originNode}</div> }
            menu={ { items } }
            onOpenChange={ handleOpenChange }
            open={ open }
            trigger={ ['click'] }
        >
            <MoreOutlined onClick={ handleClick } style={ { transform: 'rotate(90deg)' } }/>
        </Dropdown>
    )
}
