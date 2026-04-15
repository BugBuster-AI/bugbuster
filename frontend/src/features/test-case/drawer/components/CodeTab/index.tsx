import { TestCaseApi } from '@Entities/test-case/api';
import { ETestCaseType } from '@Entities/test-case/models';
import { useTestCaseStore } from '@Entities/test-case/store';
import { CodegenCopyIcon } from '@Features/test-case/playwright-codegen/CodegenPanelLayoutIcons';
import { SourceWithLineHighlights } from '@Features/test-case/playwright-codegen/SourceWithLineHighlights';
import { useQuery } from '@tanstack/react-query';
import { Alert, Button, Flex, message, Spin, Tooltip, Typography } from 'antd';
import { AxiosError } from 'axios';
import { ReactElement } from 'react';
import { useTranslation } from 'react-i18next';

/** Ключ вкладки Code в `TestCaseDrawer` (репозиторий и grouped runs). */
const CODE_TAB_KEY = '3';

export function CodeTab (): ReactElement | null {
    const { t } = useTranslation()
    const testCase = useTestCaseStore((s) => s.currentCase)
    const activeDrawerKey = useTestCaseStore((s) => s.activeDrawerKey)

    const caseId = testCase?.case_id != null ? String(testCase.case_id) : undefined
    const isManual = testCase?.type === ETestCaseType.manual
    const regenRequired = testCase?.codegen_regeneration_required === true

    const isCodeTabActive = activeDrawerKey === CODE_TAB_KEY
    const queryEnabled = Boolean(
        isCodeTabActive && caseId && !isManual && !regenRequired,
    )

    const {
        data,
        isLoading,
        isError,
        error,
        refetch,
        isFetching,
    } = useQuery({
        queryKey: ['playwright-codegen-artifact', caseId],
        queryFn: () => TestCaseApi.getInstance().getPlaywrightCodegenArtifact(caseId!),
        enabled: queryEnabled,
        retry: (failureCount, err) => {
            const ax = err as AxiosError
            const status = ax.response?.status

            if (status === 404 || status === 409) return false

            return failureCount < 2
        },
    })

    if (!isCodeTabActive) {
        return null
    }

    if (!caseId) {
        return (
            <Typography.Text type="secondary">
                {t('common.not_selected')}
            </Typography.Text>
        )
    }

    if (isManual) {
        return (
            <Alert
                message={ t('codegen.drawer_manual_case') }
                showIcon
                type="info"
            />
        )
    }

    if (regenRequired) {
        return (
            <Alert
                message={ t('codegen.drawer_regen_required') }
                showIcon
                type="warning"
            />
        )
    }

    if (isLoading || (isFetching && !data)) {
        return (
            <Flex justify="center" style={ { padding: 24 } }>
                <Spin/>
            </Flex>
        )
    }

    if (isError) {
        const ax = error as AxiosError
        const status = ax.response?.status

        if (status === 404) {
            return (
                <Alert
                    message={ t('codegen.drawer_no_code') }
                    showIcon
                    type="info"
                />
            )
        }
        if (status === 409) {
            return (
                <Alert
                    message={ t('codegen.drawer_regen_required') }
                    showIcon
                    type="warning"
                />
            )
        }

        return (
            <Flex gap={ 8 } vertical>
                <Alert
                    message={ t('common.api_error') }
                    showIcon
                    type="error"
                />
                <Button onClick={ () => void refetch() } type="primary">
                    {t('codegen.drawer_retry')}
                </Button>
            </Flex>
        )
    }

    const source = data?.source_code ?? ''

    if (!source) {
        return (
            <Alert
                message={ t('codegen.drawer_no_code') }
                showIcon
                type="info"
            />
        )
    }

    return (
        <Flex
            gap={ 8 }
            style={ { flex: 1, minHeight: 0, overflow: 'hidden' } }
            vertical
        >
            <Flex align="center" justify="space-between" style={ { flexShrink: 0, minHeight: 28 } }>
                <Typography.Text strong>
                    {t('codegen.drawer_code_title')}
                </Typography.Text>
                <Tooltip title={ t('codegen.copy_code_tooltip') }>
                    <Button
                        aria-label={ t('common.copy') }
                        icon={ <CodegenCopyIcon/> }
                        onClick={ () => {
                            navigator.clipboard.writeText(source).then(
                                () => message.success(t('common.simpleCopied')),
                                () => message.error(t('codegen.copy_failed')),
                            )
                        } }
                        size="small"
                        type="text"
                    />
                </Tooltip>
            </Flex>
            <div
                style={ {
                    display: 'flex',
                    flex: 1,
                    flexDirection: 'column',
                    minHeight: 0,
                } }
            >
                <SourceWithLineHighlights
                    fillAvailableHeight
                    highlightFrom={ null }
                    highlightTo={ null }
                    source={ source }
                />
            </div>
        </Flex>
    )
}
