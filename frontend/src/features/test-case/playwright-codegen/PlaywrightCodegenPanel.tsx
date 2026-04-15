import { runQueryKeys } from '@Entities/runs/queries/query-keys';
import { TestCaseApi } from '@Entities/test-case/api';
import {
    ICodegenArtifactResponse,
    ICodegenJobState,
    ICodegenLogEntry,
    ICodegenStatusResponse,
    ITestCase,
} from '@Entities/test-case/models';
import { caseQueries } from '@Entities/test-case/queries';
import { useTestCaseStore } from '@Entities/test-case/store/index.tsx';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
    Alert,
    Button,
    Divider,
    Flex,
    InputNumber,
    message,
    Popconfirm,
    Spin,
    Tag,
    Tooltip,
    Typography,
} from 'antd';
import { AxiosError } from 'axios';
import dayjs from 'dayjs';
import get from 'lodash/get';
import { ReactElement, useEffect, useMemo, useRef, useState } from 'react';
import { Trans, useTranslation } from 'react-i18next';
import { stripAnsi } from './codegenLogAnsi'
import { CodegenLogLine } from './CodegenLogLine'
import { CodegenCollapseLayoutIcon, CodegenCopyIcon, CodegenExpandLayoutIcon } from './CodegenPanelLayoutIcons'
import { SourceWithLineHighlights } from './SourceWithLineHighlights'

const caseApi = TestCaseApi.getInstance()

function codegenLogPlainText (log: ICodegenLogEntry[]): string {
    return log
        .map((row) => {
            const head = `[${row.level || 'info'}]`
            const phase = row.phase ? ` ${row.phase}` : ''
            const suid = row.step_uid ? ` ${row.step_uid.slice(0, 8)}…` : ''

            return `${head}${phase}${suid} ${stripAnsi(row.message ?? '')}`.trimEnd()
        })
        .join('\n')
}

function eligibilityMessageKey (reason: string | null | undefined): string {
    if (!reason) return 'codegen.eligibility.invalid_run'

    return `codegen.eligibility.${reason}`
}

function codegenJobDisplayState (job: ICodegenJobState | undefined, logLen: number): string | null {
    if (!job) return null
    const s = job.state

    if (s === 'queued' || s === 'running' || s === 'success' || s === 'failure') {
        return s
    }
    if (job.task_id || logLen > 0) {
        return 'unknown'
    }

    return null
}

type CodegenContentLayout = 'compact' | 'log_focus' | 'code_focus'

function codegenStateTagColor (state: string): 'default' | 'error' | 'gold' | 'processing' | 'success' {
    switch (state) {
        case 'queued':
            return 'gold'
        case 'running':
            return 'processing'
        case 'success':
            return 'success'
        case 'failure':
            return 'error'
        default:
            return 'default'
    }
}

interface IProps {
    caseId: string
    runId: string
    testCase: ITestCase | undefined
    /** Совпадает с step_uid в step_spans артефакта — подсветка блока кода для выбранного шага прогона */
    highlightStepUid?: string | null
    /** Встроена в основную область — без отдельного заголовка «Генерация автотеста» */
    embedded?: boolean
}

export const PlaywrightCodegenPanel = ({
    caseId,
    runId,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars -- IProps; passed for future / consistency
    testCase: _testCase,
    highlightStepUid = null,
    embedded = false,
}: IProps): ReactElement => {
    const { t } = useTranslation()
    const qc = useQueryClient()
    const [maxValidationAttempts, setMaxValidationAttempts] = useState(10)
    const [codegenContentLayout, setCodegenContentLayout] = useState<CodegenContentLayout>('compact')

    const { data: status, isLoading: statusLoading } = useQuery({
        queryKey: ['playwright-codegen-status', caseId, runId],
        queryFn: (): Promise<ICodegenStatusResponse> => caseApi.getPlaywrightCodegenStatus(caseId, runId),
        refetchInterval: (q) => {
            const st = get(q, 'state.data.job.state', null) as string | null

            return st === 'queued' || st === 'running' ? 2000 : false
        },
    })

    const startMut = useMutation({
        mutationFn: () => caseApi.startPlaywrightCodegen(caseId, runId, maxValidationAttempts),
        onMutate: async () => {
            await qc.cancelQueries({ queryKey: ['playwright-codegen-status', caseId, runId] })
            const statusKey = ['playwright-codegen-status', caseId, runId] as const
            const previousStatus = qc.getQueryData<ICodegenStatusResponse>(statusKey)
            const previousArtifact = qc.getQueryData<ICodegenArtifactResponse>([
                'playwright-codegen-artifact',
                caseId,
            ])

            if (previousStatus) {
                qc.setQueryData<ICodegenStatusResponse>(statusKey, {
                    ...previousStatus,
                    codegen_regeneration_required: false,
                    source_run_id: null,
                    job: {
                        ...previousStatus.job,
                        state: 'queued',
                        log: [],
                        error: null,
                        task_id: undefined,
                        run_id: runId,
                        max_validation_attempts: maxValidationAttempts,
                        updated_at: new Date().toISOString(),
                    },
                })
            }
            qc.removeQueries({ queryKey: ['playwright-codegen-artifact', caseId] })

            return { previousStatus, previousArtifact }
        },
        onSuccess: async () => {
            await qc.invalidateQueries({ queryKey: ['playwright-codegen-status', caseId, runId] })
        },
        onError: (err: unknown, _vars, ctx) => {
            const statusKey = ['playwright-codegen-status', caseId, runId] as const

            if (ctx?.previousStatus) {
                qc.setQueryData(statusKey, ctx.previousStatus)
            }
            if (ctx?.previousArtifact !== undefined) {
                qc.setQueryData(['playwright-codegen-artifact', caseId], ctx.previousArtifact)
            }
            const ax = err as AxiosError<{ detail?: { message_key?: string } }>
            const d = ax?.response?.data?.detail

            if (typeof d === 'object' && d?.message_key) {
                const m = t(d.message_key)

                message.error(m && m !== d.message_key ? m : t('common.api_error'))

                return
            }
            message.error(t('common.api_error'))
        },
    })

    const job = status?.job
    const jobBusy = job?.state === 'queued' || job?.state === 'running'
    const codegenInFlight = Boolean(jobBusy || startMut.isPending)
    /** Показывать артефакт только после успешной финализации последней задачи codegen (не failure/queued/running). */
    const jobSucceeded = job?.state === 'success'
    const artifactEnabled = Boolean(
        caseId
        && status?.source_run_id
        && !status?.codegen_regeneration_required
        && !codegenInFlight
        && jobSucceeded,
    )

    const { data: artifact, isLoading: artifactLoading } = useQuery({
        queryKey: ['playwright-codegen-artifact', caseId],
        queryFn: (): Promise<ICodegenArtifactResponse> => caseApi.getPlaywrightCodegenArtifact(caseId),
        enabled: artifactEnabled,
    })

    const prevRegenRef = useRef<boolean | undefined>(undefined)

    useEffect(() => {
        const cur = status?.codegen_regeneration_required

        if (cur === true && prevRegenRef.current === false) {
            qc.removeQueries({ queryKey: ['playwright-codegen-artifact', caseId] })
        }
        prevRegenRef.current = cur
    }, [status?.codegen_regeneration_required, caseId, qc])

    const deleteMut = useMutation({
        mutationFn: () => caseApi.deletePlaywrightCodegenArtifact(caseId),
        onSuccess: async () => {
            message.success(t('codegen.delete_artifact_ok'))
            await qc.invalidateQueries({ queryKey: ['playwright-codegen-artifact', caseId] })
            await qc.invalidateQueries({ queryKey: ['playwright-codegen-status', caseId, runId] })
            try {
                const c = await caseApi.getById(caseId)

                useTestCaseStore.getState().setCurrentCase(c)
            } catch {
                /* ignore */
            }
        },
        onError: () => {
            message.error(t('common.api_error'))
        },
    })

    const resetJobMut = useMutation({
        mutationFn: () => caseApi.clearPlaywrightCodegenJob(caseId),
        onSuccess: async () => {
            message.success(t('codegen.reset_job_ok'))
            await qc.invalidateQueries({ queryKey: ['playwright-codegen-status', caseId, runId] })
        },
        onError: () => {
            message.error(t('common.api_error'))
        },
    })

    const elig = status?.codegen_eligibility
    const allowed = elig?.allowed === true
    const disallowReason = elig?.reason_code
        ? t(eligibilityMessageKey(elig.reason_code))
        : null

    const regenRequired = status?.codegen_regeneration_required === true
    const jobFailed = job?.state === 'failure'
    const hideStaleJobInfo = regenRequired && !codegenInFlight && !jobFailed
    const failErr = job?.error
    const jobLog = job?.log ?? []
    const jobDisplayState = codegenJobDisplayState(job, jobLog.length)
    const LOG_TAIL_LIMIT = 200
    const [showAllLog, setShowAllLog] = useState(false)
    const hasCodegenJobInfo = Boolean(!hideStaleJobInfo && (job?.state || job?.task_id || jobLog.length > 0))
    const logEndRef = useRef<HTMLDivElement>(null)
    const prevJobStateRef = useRef<ICodegenJobState['state'] | undefined | null>(undefined)

    useEffect(() => {
        if (!jobBusy || !logEndRef.current) return
        logEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }, [jobBusy, jobLog.length])

    /**
     * После успешной генерации backend выставляет can_run_playwright_js; без refetch кэш runningCase
     * устаревает и «Запустить скрипт» остаётся disabled.
     */
    useEffect(() => {
        const st = job?.state

        if (st !== 'success' || !runId || !caseId) {
            prevJobStateRef.current = st

            return
        }
        if (prevJobStateRef.current === 'success') {
            return
        }
        prevJobStateRef.current = st
        void (async () => {
            await qc.invalidateQueries({ queryKey: [runQueryKeys.runningCase, runId] })
            await qc.invalidateQueries({ queryKey: [...caseQueries.all(), caseId] })
            try {
                const c = await caseApi.getById(caseId)

                useTestCaseStore.getState().setCurrentCase(c)
            } catch {
                /* ignore */
            }
        })()
    }, [job?.state, runId, caseId, qc])

    const sourceMismatch = Boolean(
        status?.source_run_id && runId && status.source_run_id !== runId,
    )

    const bannerNoCode = Boolean(status?.codegen_regeneration_required && !status?.source_run_id)

    const canDeleteArtifact = Boolean(artifact?.artifact_id && !jobBusy)

    const highlightRange = useMemo(() => {
        if (!highlightStepUid || !artifact?.step_spans?.length) {
            return { from: null as number | null, to: null as number | null }
        }
        const sp = artifact.step_spans.find((s) => s.step_uid === highlightStepUid)

        if (!sp) return { from: null, to: null }

        return { from: sp.start_line, to: sp.end_line }
    }, [artifact, highlightStepUid])

    const hasGeneratedCodeBlock = Boolean(artifactEnabled && artifact && !artifactLoading)
    const logLayoutHidden = embedded && hasGeneratedCodeBlock && codegenContentLayout === 'code_focus'
    const codeLayoutHidden = embedded && hasGeneratedCodeBlock && codegenContentLayout === 'log_focus'
    const showLogSection = jobLog.length > 0 && !hideStaleJobInfo && !logLayoutHidden
    const logFillsRemainingHeight = embedded && (!hasGeneratedCodeBlock || codegenContentLayout === 'log_focus')
    const codeFillsRemainingHeight = embedded && hasGeneratedCodeBlock && codegenContentLayout === 'code_focus'
    const prevHadGeneratedCodeRef = useRef(false)

    useEffect(() => {
        if (!prevHadGeneratedCodeRef.current && hasGeneratedCodeBlock) {
            setCodegenContentLayout('compact')
        }
        prevHadGeneratedCodeRef.current = hasGeneratedCodeBlock
    }, [hasGeneratedCodeBlock])

    const genLogExpandTooltip = codegenContentLayout === 'log_focus'
        ? t('codegen.collapse_log_tooltip')
        : t('codegen.expand_log_tooltip')
    const genLogExpandLabel = codegenContentLayout === 'log_focus' ? t('codegen.collapse_log') : t('codegen.expand_log')
    const genCodeExpandTooltip = codegenContentLayout === 'code_focus'
        ? t('codegen.collapse_code_tooltip')
        : t('codegen.expand_code_tooltip')
    const genCodeExpandLabel = codegenContentLayout === 'code_focus'
        ? t('codegen.collapse_code')
        : t('codegen.expand_code')

    if (statusLoading && !status) {
        return (
            <Flex justify="center" style={ { marginBottom: 12 } }>
                <Spin/>
            </Flex>
        )
    }

    return (
        <Flex
            gap={ 8 }
            style={ {
                marginBottom: embedded ? 0 : 16,
                ...(embedded ? { flex: 1, minHeight: 0, width: '100%' } : {}),
            } }
            vertical
        >
            {!embedded && (
                <Divider orientation="left" orientationMargin={ 0 } style={ { margin: '8px 0' } } plain>
                    <Typography.Title level={ 5 } style={ { margin: 0 } }>
                        {t('codegen.panel_title')}
                    </Typography.Title>
                </Divider>
            )}

            {status?.codegen_regeneration_required && !codegenInFlight && (
                <Alert
                    description={
                        bannerNoCode
                            ? t('codegen.banner_body_nocode')
                            : t('codegen.banner_body_stale')
                    }
                    message={ t('codegen.banner_title') }
                    type="warning"
                    showIcon
                />
            )}

            {sourceMismatch && (
                <Typography.Text type="secondary">
                    <Trans
                        components={ { code: <Typography.Text code/> } }
                        i18nKey="codegen.artifact_source_mismatch"
                        values={ { sourceRunId: status?.source_run_id } }
                    />
                </Typography.Text>
            )}

            <Flex align="center" gap={ 12 } wrap="wrap">
                <Flex align="center" gap={ 6 }>
                    <Typography.Text type="secondary">
                        {t('codegen.max_validation_attempts_label')}
                    </Typography.Text>
                    <Tooltip title={ t('codegen.max_validation_attempts_tooltip') }>
                        <InputNumber
                            changeOnWheel={ false }
                            disabled={ jobBusy || startMut.isPending }
                            max={ 20 }
                            min={ 1 }
                            onChange={ (v) => {
                                const n = typeof v === 'number' ? v : 10

                                setMaxValidationAttempts(Number.isFinite(n) ? Math.min(20, Math.max(1, n)) : 10)
                            } }
                            size="small"
                            value={ maxValidationAttempts }
                        />
                    </Tooltip>
                </Flex>

                <Tooltip title={ !allowed && disallowReason ? disallowReason : undefined }>
                    <Button
                        disabled={ !allowed || jobBusy || startMut.isPending }
                        loading={ startMut.isPending || jobBusy }
                        onClick={ () => startMut.mutate() }
                        type="primary"
                    >
                        {status?.source_run_id ? t('codegen.retry_generate') : t('codegen.generate')}
                    </Button>
                </Tooltip>

                <Popconfirm
                    disabled={ !canDeleteArtifact || deleteMut.isPending }
                    okButtonProps={ { danger: true } }
                    onConfirm={ () => deleteMut.mutate() }
                    title={ t('codegen.delete_artifact_confirm') }
                >
                    <Button
                        disabled={ !canDeleteArtifact || deleteMut.isPending }
                        loading={ deleteMut.isPending }
                        danger
                    >
                        {t('codegen.delete_artifact')}
                    </Button>
                </Popconfirm>

                {jobBusy && (
                    <Popconfirm
                        disabled={ resetJobMut.isPending }
                        okButtonProps={ { danger: true } }
                        onConfirm={ () => resetJobMut.mutate() }
                        title={ t('codegen.reset_job_confirm') }
                    >
                        <Button
                            disabled={ resetJobMut.isPending }
                            loading={ resetJobMut.isPending }
                        >
                            {t('codegen.reset_job')}
                        </Button>
                    </Popconfirm>
                )}
            </Flex>

            {hasCodegenJobInfo && (
                <Flex
                    gap={ 8 }
                    style={ {
                        background: 'var(--ant-color-fill-quaternary, #f5f5f5)',
                        borderRadius: 8,
                        padding: '8px 12px',
                    } }
                    vertical
                >
                    <Flex align="center" gap={ 8 } wrap="wrap">
                        <Typography.Text strong>{t('codegen.job_status_title')}</Typography.Text>
                        {jobDisplayState
                            ? (
                                <Tag color={ codegenStateTagColor(jobDisplayState) }>
                                    {t(`codegen.job_state.${jobDisplayState}`)}
                                </Tag>
                            )
                            : null}
                    </Flex>
                    <Flex align="center" gap={ 12 } wrap="wrap">
                        {job?.updated_at
                            ? (
                                <Typography.Text type="secondary">
                                    {t('codegen.job_updated_at', {
                                        time: dayjs(job.updated_at).format('DD.MM.YYYY HH:mm:ss'),
                                    })}
                                </Typography.Text>
                            )
                            : null}
                        {job?.task_id
                            ? (
                                <Typography.Text type="secondary">
                                    {t('codegen.job_task_id')}
                                    {': '}
                                    <Typography.Text copyable={ { text: job.task_id } } code>
                                        {`${job.task_id.slice(0, 8)}…`}
                                    </Typography.Text>
                                </Typography.Text>
                            )
                            : null}
                        {job?.max_validation_attempts != null
                            ? (
                                <Typography.Text type="secondary">
                                    {t('codegen.job_max_attempts', { n: job.max_validation_attempts })}
                                </Typography.Text>
                            )
                            : null}
                    </Flex>
                </Flex>
            )}

            {jobBusy && !hideStaleJobInfo && jobLog.length === 0 && (
                <Alert message={ t('codegen.job_no_log_yet') } type="info" showIcon />
            )}

            {jobFailed && !hideStaleJobInfo && failErr && (() => {
                const reasonKey = failErr.reason_code
                    ? `codegen.failure_reason.${failErr.reason_code}`
                    : ''
                const reasonLabel = reasonKey ? t(reasonKey) : ''
                const title = (reasonLabel && reasonLabel !== reasonKey)
                    ? reasonLabel
                    : t('codegen.eligibility.codegen_failed')
                const detail = failErr.step_uid
                    ? `${failErr.message || ''} (step_uid: ${failErr.step_uid})`
                    : (failErr.message || '')

                return (
                    <Alert
                        description={ detail || undefined }
                        message={ title }
                        type="error"
                        showIcon
                    />
                )
            })()}

            {showLogSection && (
                <Flex
                    gap={ 4 }
                    style={
                        logFillsRemainingHeight
                            ? { flex: 1, minHeight: 0 }
                            : undefined
                    }
                    vertical
                >
                    <Flex align="center" justify="space-between" style={ { flexShrink: 0, minHeight: 28 } }>
                        <Typography.Text strong>{t('codegen.generation_log')}</Typography.Text>
                        <Flex align="center" gap={ 4 }>
                            {embedded && hasGeneratedCodeBlock && (
                                <Tooltip title={ genLogExpandTooltip }>
                                    <Button
                                        aria-label={ genLogExpandLabel }
                                        aria-pressed={ codegenContentLayout === 'log_focus' }
                                        icon={ codegenContentLayout === 'log_focus'
                                            ? <CodegenCollapseLayoutIcon/>
                                            : <CodegenExpandLayoutIcon/> }
                                        onClick={ () => setCodegenContentLayout((prev) => (
                                            prev === 'log_focus' ? 'compact' : 'log_focus'
                                        )) }
                                        size="small"
                                        type="text"
                                    />
                                </Tooltip>
                            )}
                            <Tooltip title={ t('codegen.copy_log_tooltip') }>
                                <Button
                                    icon={ <CodegenCopyIcon/> }
                                    onClick={ () => {
                                        navigator.clipboard.writeText(codegenLogPlainText(jobLog)).then(
                                            () => message.success(t('common.simpleCopied')),
                                            () => message.error(t('codegen.copy_failed')),
                                        )
                                    } }
                                    size="small"
                                    type="text"
                                />
                            </Tooltip>
                        </Flex>
                    </Flex>
                    <div
                        style={ {
                            background: 'var(--ant-color-fill-quaternary, #f5f5f5)',
                            borderRadius: 8,
                            flex: logFillsRemainingHeight ? 1 : undefined,
                            fontFamily: 'monospace',
                            fontSize: 12,
                            lineHeight: 1.6,
                            margin: 0,
                            minHeight: logFillsRemainingHeight ? 0 : undefined,
                            ...(hasGeneratedCodeBlock && codegenContentLayout === 'compact' ? { maxHeight: 280 } : {}),
                            overflow: 'auto',
                            padding: 12,
                        } }
                    >
                        {(() => {
                            const truncated = !showAllLog && jobLog.length > LOG_TAIL_LIMIT
                            const visibleLog = truncated ? jobLog.slice(-LOG_TAIL_LIMIT) : jobLog
                            const offset = truncated ? jobLog.length - LOG_TAIL_LIMIT : 0

                            return (
                                <>
                                    {truncated && (
                                        <div style={ { marginBottom: 4 } }>
                                            <Button
                                                onClick={ () => setShowAllLog(true) }
                                                size="small"
                                                type="link"
                                            >
                                                {t('codegen.show_all_log', { count: jobLog.length })}
                                            </Button>
                                        </div>
                                    )}
                                    {visibleLog.map((row, i) => (
                                        <CodegenLogLine key={ `log-${offset + i}-${row.t ?? ''}` } row={ row }/>
                                    ))}
                                </>
                            )
                        })()}
                        <div ref={ logEndRef }/>
                    </div>
                </Flex>
            )}

            {artifactEnabled && artifactLoading && !codeLayoutHidden && (
                <Spin style={ { flexShrink: 0 } }/>
            )}
            {artifactEnabled && !artifactLoading && artifact && !codeLayoutHidden && (
                <Flex
                    gap={ 6 }
                    style={ codeFillsRemainingHeight ? { flex: 1, minHeight: 0 } : { flexShrink: 0 } }
                    vertical
                >
                    <Flex align="center" justify="space-between" style={ { flexShrink: 0, minHeight: 28 } }>
                        <Typography.Text strong>{t('codegen.generated_code_title')}</Typography.Text>
                        <Flex align="center" gap={ 4 }>
                            {embedded && hasGeneratedCodeBlock && (
                                <Tooltip title={ genCodeExpandTooltip }>
                                    <Button
                                        aria-label={ genCodeExpandLabel }
                                        aria-pressed={ codegenContentLayout === 'code_focus' }
                                        icon={ codegenContentLayout === 'code_focus'
                                            ? <CodegenCollapseLayoutIcon/>
                                            : <CodegenExpandLayoutIcon/> }
                                        onClick={ () => setCodegenContentLayout((prev) => (
                                            prev === 'code_focus' ? 'compact' : 'code_focus'
                                        )) }
                                        size="small"
                                        type="text"
                                    />
                                </Tooltip>
                            )}
                            <Tooltip title={ t('codegen.copy_code_tooltip') }>
                                <Button
                                    icon={ <CodegenCopyIcon/> }
                                    onClick={ () => {
                                        navigator.clipboard.writeText(artifact.source_code ?? '').then(
                                            () => message.success(t('common.simpleCopied')),
                                            () => message.error(t('codegen.copy_failed')),
                                        )
                                    } }
                                    size="small"
                                    type="text"
                                />
                            </Tooltip>
                        </Flex>
                    </Flex>
                    <SourceWithLineHighlights
                        fillAvailableHeight={ codeFillsRemainingHeight }
                        highlightFrom={ highlightRange.from }
                        highlightTo={ highlightRange.to }
                        source={ artifact.source_code }
                    />
                </Flex>
            )}
        </Flex>
    )
}
