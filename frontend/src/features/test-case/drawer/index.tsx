import { URL_QUERY_KEYS } from '@Common/consts/searchParams.ts';
import { useThemeToken } from '@Common/hooks';
import { useTestCaseStore } from '@Entities/test-case/store';
import { CodeTab } from '@Features/test-case/drawer/components/CodeTab';
import { ExtraTabButtons } from '@Features/test-case/drawer/components/ExtraTabButtons';
import { GeneralInfo } from '@Features/test-case/drawer/components/GeneralInfo';
import { TestCaseRunsHistory } from '@Features/test-case/runs-history';
import { Button, Drawer, Flex, Tabs, TabsProps, Tooltip, Typography } from 'antd';
import { Maximize2, Minimize2 } from 'lucide-react';
import { ReactNode, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router-dom';

import styles from './index.module.scss';

/** Обычная ширина дровера (доля viewport). Развёрнутая — см. `DRAWER_WIDTH_EXPANDED_VW`. */
const DRAWER_WIDTH_COMPACT_VW = '48vw'
const DRAWER_WIDTH_EXPANDED_VW = '80vw'

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
    const [expandedWidth, setExpandedWidth] = useState(false)
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
            children: (
                <div className={ styles.tabPaneScroll }>
                    <GeneralInfo/>
                </div>
            ),

        },
        {
            key: '2',
            label: t('drawerTabs.run_history'),
            children: (
                <div className={ styles.tabPaneScroll }>
                    <TestCaseRunsHistory/>
                </div>
            ),
        },
        {
            key: '3',
            children: (
                <div className={ styles.codeTabPane }>
                    <CodeTab/>
                </div>
            ),
            destroyInactiveTabPane: true,
            label: t('drawerTabs.codegen'),
        },
    ]

    const clearParams = () => {
        updateSearchParams((prev) => {
            prev.delete(URL_QUERY_KEYS.DRAWER_STATE)
            prev.delete(URL_QUERY_KEYS.CASE_ID)
            prev.delete(URL_QUERY_KEYS.OPEN)

            return prev
        })
    }

    const handleClose = () => {
        onClose?.()
    }

    /** Чтобы не сбрасывать `caseId` из URL при первом монтировании с закрытым дровером (deep link: только подсветка строки). */
    const drawerWasOpenRef = useRef(false)

    useEffect(() => {
        if (!setSearchParamsOnOpen || !open || !currentCase) return

        updateSearchParams((prev) => {
            prev.set(URL_QUERY_KEYS.CASE_ID, String(currentCase.case_id))
            prev.set(URL_QUERY_KEYS.OPEN, '1')

            return prev
        })
    }, [setSearchParamsOnOpen, open, currentCase, updateSearchParams])

    useEffect(() => {
        if (!setSearchParamsOnOpen) return

        const wasOpen = drawerWasOpenRef.current
        drawerWasOpenRef.current = Boolean(open)

        if (!open && wasOpen) {
            clearParams()
        }
    }, [setSearchParamsOnOpen, open])

    const handleOpenChange = (open: boolean) => {
        afterOpenChange?.(open)
        if (!open) {
            setActiveKey('1')
            setExpandedWidth(false)
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

    const drawerWidth = expandedWidth ? DRAWER_WIDTH_EXPANDED_VW : DRAWER_WIDTH_COMPACT_VW

    const widthToggleButton = (
        <Tooltip
            title={ expandedWidth
                ? t('drawerLayout.restore_width_tooltip')
                : t('drawerLayout.expand_to_80_tooltip') }
        >
            <Button
                aria-label={ expandedWidth
                    ? t('drawerLayout.restore_width_tooltip')
                    : t('drawerLayout.expand_to_80_tooltip') }
                icon={ expandedWidth
                    ? (
                        <Minimize2
                            aria-hidden
                            size={ 16 }
                            strokeWidth={ 2 }
                        />
                    )
                    : (
                        <Maximize2
                            aria-hidden
                            size={ 16 }
                            strokeWidth={ 2 }
                        />
                    ) }
                onClick={ () => setExpandedWidth((v) => !v) }
                size="small"
                type="text"
            />
        </Tooltip>
    )

    return (
        <Drawer
            afterOpenChange={ handleOpenChange }
            destroyOnClose
            extra={ widthToggleButton }
            onClose={ handleClose }
            open={ open }
            style={ { position: 'relative' } }
            styles={ {
                body: {
                    display: 'flex',
                    flexDirection: 'column',
                    height: '100%',
                    minHeight: 0,
                    overflow: 'hidden',
                },
            } }
            title={ titleComponent || (
                <Flex vertical>
                    <Typography.Text>{currentCase?.name}</Typography.Text>
                    <Typography.Text style={ { fontSize: '12px', color: token.colorTextDescription } }>
                        {currentCase?.case_id}
                    </Typography.Text>
                </Flex>
            ) }
            width={ drawerWidth }
        >
            <Flex className={ styles.rootInner } vertical>
                {!!currentCase?.description && showCaseDescription && (
                    <Typography.Text style={ { display: 'block', flexShrink: 0, paddingBottom: 16 } }>
                        {currentCase?.description}
                    </Typography.Text>
                )}
                {underTabButtons}

                <Tabs
                    activeKey={ activeKey }
                    className={ styles.tabsFill }
                    items={ menuItems || items }
                    onChange={ setActiveKey }
                    tabBarExtraContent={ {
                        right: rightButtons
                    } }
                />

                {bodyBottomSlot}
            </Flex>
        </Drawer>
    )

}
