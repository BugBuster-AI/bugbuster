import { DeleteOutlined, PlusOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { EExecutionMode } from '@Entities/runs/models/enum';
import { runsQueries } from '@Entities/runs/queries';
import { ICaseWithExecution, useCreateRunStore } from '@Features/runs/create-run-from-cases/store';
import { useQuery } from '@tanstack/react-query';
import { Badge, Button, Card, Flex, InputNumber, Space, Typography } from 'antd';
import flatMap from 'lodash/flatMap';
import map from 'lodash/map';
import size from 'lodash/size';
import values from 'lodash/values';
import { useTranslation } from 'react-i18next';
import { useParams } from 'react-router-dom';

export const ParallelCasesForm = () => {
    const { t } = useTranslation()
    const { id } = useParams()
    
    const selectedCases = useCreateRunStore((state) => state.selectedCaseId)
    const setSelectedCases = useCreateRunStore((state) => state.setCaseId)
    const setStep = useCreateRunStore((state) => state.setStep)
    const setExecutionMode = useCreateRunStore((state) => state.setExecutionMode)
    const maxParallelThreads = useCreateRunStore((state) => state.maxParallelThreads)
    const selectedParallelThreads = useCreateRunStore((state) => state.selectedParallelThreads)
    const setSelectedParallelThreads = useCreateRunStore((state) => state.setSelectedParallelThreads)

    // Get parallel cases from selectedCases
    const parallelCases = flatMap(values(selectedCases), (cases) =>
        map(cases, (c: ICaseWithExecution) =>
            c.executionMode === 'parallel' && c
        ).filter(Boolean)
    ) as ICaseWithExecution[]

    const parallelCasesCount = size(parallelCases)

    // Get max parallel threads from API
    const { data: freeStreams, isLoading } = useQuery(runsQueries.freeStreams(id!, {
        enabled: !!id
    }))

    const maxThreads = maxParallelThreads || (freeStreams ? Number(freeStreams) : 1)

    const handleAddParallelCases = () => {
        setExecutionMode(EExecutionMode.PARALLEL)
        setStep(2)
    }

    const handleClearParallelCases = () => {
        // Filter out all parallel cases
        const updatedCases = Object.entries(selectedCases).reduce((acc, [suiteId, cases]) => {
            const filtered = cases.filter((c: ICaseWithExecution) => c.executionMode !== 'parallel')

            if (filtered.length > 0) {
                acc[suiteId] = filtered
            }

            return acc
        }, {} as Record<string, ICaseWithExecution[]>)

        setSelectedCases(updatedCases)
    }

    const handleThreadsChange = (value: number | null) => {
        if (value !== null) {
            setSelectedParallelThreads(value)
        }
    }

    return (
        <Card
            extra={
                <Space size={ 4 }>
                    <Button
                        icon={ <PlusOutlined /> }
                        onClick={ handleAddParallelCases }
                        size="small"
                        type="link"
                    >
                        {'Add'}
                    </Button>
                    {parallelCasesCount > 0 && (
                        <Button
                            icon={ <DeleteOutlined /> }
                            onClick={ handleClearParallelCases }
                            size="small"
                            type="link"
                            danger
                        >
                            {'Clear'}
                        </Button>
                    )}
                </Space>
            }
            size="small"
            title={
                <Flex align="center" gap={ 8 }>
                    <ThunderboltOutlined style={ { color: '#1677ff' } } />
                    <span>{t('create_run.parallel_cases')}</span>
                    <Badge
                        count={ parallelCasesCount }
                        showZero
                        style={ { backgroundColor: parallelCasesCount > 0 ? '#1677ff' : '#d9d9d9' } }
                    />
                </Flex>
            }
        >
            <Flex align="center" gap={ 12 }>
                <InputNumber
                    disabled={ isLoading }
                    max={ maxThreads }
                    min={ 1 }
                    onChange={ handleThreadsChange }
                    size="small"
                    style={ { width: 80 } }
                    value={ selectedParallelThreads }
                />
                <Typography.Text type="secondary">
                    {t('create_run.threads_label')}
                </Typography.Text>
            </Flex>
        </Card>
    )
}
