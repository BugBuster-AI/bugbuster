import { URL_QUERY_KEYS } from '@Common/consts/searchParams.ts';
import { useThemeToken } from '@Common/hooks';
import { useTestCaseStore } from '@Entities/test-case/store';
import { ExtraTabButtons } from '@Features/test-case/drawer/components/ExtraTabButtons';
import { GeneralInfo } from '@Features/test-case/drawer/components/GeneralInfo';
import { TestCaseRunsHistory } from '@Features/test-case/runs-history';
import { Drawer, Flex, Tabs, TabsProps, Typography } from 'antd';
import { ReactNode, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router-dom';

interface IProps {
    items?: TabsProps['items']
    onClose: () => void
    open?: boolean
    extraRightButtons?: ReactNode
    underTabButtons?: ReactNode
    titleComponent?: ReactNode
    afterOpenChange?: (open?: boolean) => void
    setSearchParamsOnOpen?: boolean
    setSearchParamsOnChange?: boolean
    bodyBottomSlot?: ReactNode
    showCaseDescription?: boolean
}

export const TestCaseDrawer = ({
    items: menuItems,
    open,
    onClose,
    extraRightButtons,
    setSearchParamsOnOpen,
    underTabButtons,
    titleComponent,
    setSearchParamsOnChange,
    afterOpenChange,
    bodyBottomSlot,
    showCaseDescription = true
}: IProps) => {
    const [, updateSearchParams] = useSearchParams()
    const token = useThemeToken()
    const { t } = useTranslation()
    const activeKey = useTestCaseStore((state) => state.activeDrawerKey)
    const setActiveKey = useTestCaseStore((state) => state.setActiveDrawerKey)
    const currentCase = useTestCaseStore((state) => state.currentCase)
    const rightButtons = extraRightButtons === null ? null : extraRightButtons ||
        <ExtraTabButtons caseId={ currentCase?.case_id as string } onClose={ onClose }/>

    const items: TabsProps['items'] = [
        {
            key: '1',
            label: t('drawerTabs.general'),
            children: <GeneralInfo/>,

        },
        {
            key: '2',
            label: t('drawerTabs.run_history'),
            children: <TestCaseRunsHistory/>
        }
    ]

    const clearParams = () => {
        updateSearchParams((prev) => {
            prev.delete(URL_QUERY_KEYS.DRAWER_STATE)
            prev.delete(URL_QUERY_KEYS.CASE_ID)

            return prev
        })
    }

    const handleClose = () => {
        onClose?.()
    }

    useEffect(() => {
        if (setSearchParamsOnOpen) {
            if (!currentCase) return
            if (open) {
                updateSearchParams((prev) => {
                    prev.set(URL_QUERY_KEYS.CASE_ID, currentCase.case_id)

                    return prev
                })
            }
        }

        if (!open) {
            clearParams()
        }
    }, [setSearchParamsOnOpen, open, currentCase]);

    const handleOpenChange = (open: boolean) => {
        afterOpenChange?.(open)
        if (!open) {
            setActiveKey('1')
        }
    }

    useEffect(() => {
        if (setSearchParamsOnChange && open) {
            updateSearchParams((prev) => {
                prev.set(URL_QUERY_KEYS.DRAWER_STATE, activeKey)

                return prev
            })
        }
    }, [setSearchParamsOnChange, activeKey, open]);

    return (
        <Drawer
            afterOpenChange={ handleOpenChange }
            onClose={ handleClose }
            open={ open }
            style={ { position: 'relative' } }
            title={ titleComponent || (
                <Flex vertical>
                    <Typography.Text>{currentCase?.name}</Typography.Text>
                    <Typography.Text style={ { fontSize: '12px', color: token.colorTextDescription } }>
                        {currentCase?.case_id}
                    </Typography.Text>
                </Flex>
            ) }
            width={ 720 }
            destroyOnClose
        >
            {!!currentCase?.description && showCaseDescription && (
                <Typography.Text style={ { display: 'block', paddingBottom: 16 } }>
                    {currentCase?.description}
                </Typography.Text>
            )}
            {underTabButtons}

            <Tabs
                activeKey={ activeKey }
                items={ menuItems || items }
                onChange={ setActiveKey }
                tabBarExtraContent={ {
                    right: rightButtons
                } }
            />

            {bodyBottomSlot}
        </Drawer>
    )

}
