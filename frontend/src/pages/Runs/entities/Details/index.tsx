import { BaseLayout } from '@Common/components';
import { BaseFlex } from '@Common/components/BaseLayout';
import { PATHS } from '@Common/consts';
import { URL_QUERY_KEYS } from '@Common/consts/searchParams.ts';
import { LayoutTitle } from '@Components/LayoutTitle';
import { GroupCaseDrawer } from '@Pages/Runs/entities/Details/components/Drawer';
import { TitleText } from '@Pages/Runs/entities/Details/components/TitleText';
import { useRunData } from '@Pages/Runs/entities/Details/hooks';
import { useGroupedRunStore } from '@Pages/Runs/entities/Details/store';
import { Flex, Result } from 'antd';
import { ReactElement, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams, useSearchParams } from 'react-router-dom';
import { ParallelSection, SequentialSection, Toolbar, TitleBar } from './components';

export const RunsDetailsPage = (): ReactElement => {
    const { id } = useParams()
    const { t } = useTranslation()

    const { isError, isLoading } = useRunData()
    const clear = useGroupedRunStore((state) => state.clear)
    const isDrawerOpen = useGroupedRunStore((state) => state.isDrawerOpen)
    const setDrawerOpen = useGroupedRunStore((state) => state.setDrawerOpen)
    const setOpenedCaseId = useGroupedRunStore((state) => state.setOpenedCaseId)
    const [, updateSearchParams] = useSearchParams()

    useEffect(() => {
        return () => {
            clear()
        }
    }, []);

    const handleCloseDrawer = () => {
        setDrawerOpen(false)
        setOpenedCaseId(undefined)
        updateSearchParams((prev) => {
            prev.delete(URL_QUERY_KEYS.CASE_ID)

            return prev
        })
    }

    if (isError) {
        return <Result status={ '500' } title={ t('common.default_error') }/>
    }

    return (
        <Flex style={ { height: '100%' } } vertical>
            <LayoutTitle
                backPath={ id ? PATHS.RUNS.ABSOLUTE(id) : undefined }
                extra={ <TitleBar/> }
                style={ { flexWrap: 'wrap' } }
                title={ <TitleText loading={ isLoading }/> }
                withBack
            />

            <BaseFlex style={ { display: 'flex', justifyContent: 'space-between' } }>
                <Toolbar/>
            </BaseFlex>

            <BaseLayout style={ { overflow: 'auto' } }>
                <Flex gap={ 24 } vertical>
                    <SequentialSection/>
                    <ParallelSection/>
                </Flex>
            </BaseLayout>

            {isDrawerOpen && (
                <GroupCaseDrawer onClose={ handleCloseDrawer }/>
            )}
        </Flex>
    )
}
