import { MoreOutlined } from '@ant-design/icons';
import { ConfirmButton } from '@Common/components';
import { asyncHandler } from '@Common/utils';
import { IRun } from '@Entities/runs/models';
import { useCloneRun, useDeleteGroupRun } from '@Entities/runs/queries/mutations.ts';
import { CreateRunFromCases } from '@Features/runs/create-run-from-cases';
import { useCreateRunStore } from '@Features/runs/create-run-from-cases/store';
import { transformCases } from '@Features/runs/list/helper.ts';
import { Button, Dropdown, MenuProps, Typography } from 'antd';
import { memo, MouseEvent, ReactElement, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

interface IProps {
    record?: IRun
}


export const DropDownRunsButton = memo(({ record }: IProps): ReactElement => {
    const { mutateAsync } = useDeleteGroupRun()
    const { t } = useTranslation()
    const [open, setOpen] = useState(false)
    const setSelectedCases = useCreateRunStore((state) => state.setCaseId)
    const setInitialData = useCreateRunStore((state) => state.setInitialData)
    const setEdit = useCreateRunStore((state) => state.setIsEdit)
    const cloneRun = useCloneRun()

    const items: MenuProps['items'] = useMemo(() => [
        /*
         * {
         *     style: { width: 200 },
         *     key: 'runs-list-dropdown-statistics',
         *     label: t('group_run.list_dropdown.statistics'),
         * },
         */
        {
            key: 'runs-list-dropdown-clone',
            label: t('group_run.list_dropdown.clone'),
            onClick: async () => {
                if (!record?.id) {
                    return
                }

                await asyncHandler(() => cloneRun.mutateAsync([record?.id]), {})
            },
        },


        {
            key: 'runs-list-dropdown-edit',
            style: { padding: 0 },
            label: (
                <CreateRunFromCases
                    renderButton={ ({ onClick }) => {
                        const handleClick = (e) => {
                            const data = transformCases(record?.data)

                            setOpen(false)
                            setEdit()
                            setSelectedCases(data)
                            setInitialData(record)
                            onClick()
                            e.stopPropagation()
                        }

                        return (
                            <Typography.Text
                                key={ 'runs-list-dropdown-edit' }
                                onClick={ handleClick }
                                style={ { display: 'block', padding: '4px 12px' } }>
                                {t('group_run.list_dropdown.edit')}
                            </Typography.Text>
                        )
                    } }
                />
            )
        },
        {
            key: 'runs-list-dropdown-delete',
            style: { padding: 0 },
            label: (
                <ConfirmButton
                    modalProps={ {
                        centered: true,
                        title: t('group_run.list_dropdown.delete'),
                        onOk: async () => {
                            setOpen(false)
                            await asyncHandler(mutateAsync.bind(null, record?.id!!))
                        }
                    } }
                    renderButton={ ({ onClick }) => (
                        <Typography.Text
                            onClick={ () => {
                                setOpen(false)
                                onClick()
                            } }
                            style={ {
                                display: 'block',
                                padding: '4px 12px'
                            } }
                        >
                            {t('group_run.list_dropdown.delete')}
                        </Typography.Text>)
                    }
                    closeAfterOk>
                    <Typography.Text>
                        {t('group_run.list_dropdown.delete_body')}
                    </Typography.Text>
                </ConfirmButton>
            ),
        }

    ], [open])

    const handleClick = (e: MouseEvent) => {
        e.stopPropagation()
        setOpen(!open)
    }

    const handleOpenChange = () => {
        setOpen(false);
    };

    return (
        <Dropdown
            dropdownRender={ (originNode) => <div onClick={ (e) => e.stopPropagation() }>{originNode}</div> }
            menu={ { items } as MenuProps }
            onOpenChange={ handleOpenChange }
            open={ open }
            trigger={ ['click'] }
        >
            <Button
                icon={ <MoreOutlined style={ { transform: 'rotate(90deg)' } }/> }
                onClick={ handleClick }
                type={ 'text' }
            />
        </Dropdown>
    )
})
