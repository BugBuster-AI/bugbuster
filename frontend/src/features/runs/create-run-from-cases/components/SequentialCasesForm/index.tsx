import { DeleteOutlined, HolderOutlined, OrderedListOutlined, PlusOutlined } from '@ant-design/icons';
import { DndContext, DragEndEvent, KeyboardSensor, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { SortableContext, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { EExecutionMode } from '@Entities/runs/models/enum';
import { TestPriorityIcon, TestTypeIcon } from '@Entities/test-case/components/Icons';
import { ETestCasePriority } from '@Entities/test-case/models';
import { ICaseWithExecution, useCreateRunStore } from '@Features/runs/create-run-from-cases/store';
import VirtualList from '@rc-component/virtual-list';
import { Badge, Button, Card, Empty, Flex, Space, Tag, Typography } from 'antd';
import cloneDeep from 'lodash/cloneDeep';
import flatMap from 'lodash/flatMap';
import map from 'lodash/map';
import size from 'lodash/size';
import values from 'lodash/values';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';

interface ISortableItemProps {
    id: string
    index: number
    onDelete: (id: string) => void
    item: ICaseWithExecution
}

const ITEM_HEIGHT = 42

const SortableItem = ({ id, index, onDelete, item }: ISortableItemProps) => {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging
    } = useSortable({ id })

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : 1,
    }

    const caseData = item.caseData

    return (
        <div ref={ setNodeRef } style={ { ...style, paddingBottom: 4 } }>
            <Flex
                align="center"
                justify="space-between"
                style={ {
                    backgroundColor: '#fafafa',
                    border: '1px solid #f0f0f0',
                    borderRadius: 6,
                    padding: '4px 8px',
                } }
            >
                <Flex align="center" gap={ 6 } style={ { minWidth: 0, flex: 1 } }>
                    <Button
                        icon={ <HolderOutlined /> }
                        size="small"
                        type="text"
                        { ...attributes }
                        { ...listeners }
                        style={ { cursor: 'grab', minWidth: 24, width: 24, height: 24 } }
                    />
                    <TestTypeIcon type={ caseData?.type }/>
                    <TestPriorityIcon priority={ caseData.priority as ETestCasePriority }/>
                    <Tag color="blue" style={ { margin: 0 } }>{index + 1}</Tag>
                    <Typography.Text ellipsis style={ { fontSize: 13 } }>{caseData.name}</Typography.Text>
                </Flex>
                <Button
                    icon={ <DeleteOutlined /> }
                    onClick={ () => onDelete(id) }
                    size="small"
                    style={ { minWidth: 24, width: 24, height: 24 } }
                    type="text"
                    danger
                />
            </Flex>
        </div>
    )
}

export const SequentialCasesForm = () => {
    const { t } = useTranslation()
    const selectedCases = useCreateRunStore((state) => state.selectedCaseId)
    const setSelectedCases = useCreateRunStore((state) => state.setCaseId)
    const selectedSuiteId = useCreateRunStore((state) => state.selectedSuiteId)
    const setSelectedSuites = useCreateRunStore((state) => state.setSuiteId)
    const setStep = useCreateRunStore((state) => state.setStep)
    const setExecutionMode = useCreateRunStore((state) => state.setExecutionMode)

    const sensors = useSensors(
        useSensor(PointerSensor),
        useSensor(KeyboardSensor)
    )
    
    // Get sequential cases from selectedCases
    const sequentialCases = useMemo(() => {
        return flatMap(values(selectedCases), (cases) =>
            map(cases, (c: ICaseWithExecution) =>
                (c.executionMode === EExecutionMode.SEQUENTIAL ? c : null)
            ).filter(Boolean)
        ) as ICaseWithExecution[]
    }, [selectedCases])

    const sequentialCasesCount = size(sequentialCases)

    // Sort sequential cases by executionOrder if present, else by index in flat list
    const sortedSequentialCases = useMemo(() => {
        return [...sequentialCases].sort((a, b) => {
            return (a.executionOrder ?? 0) - (b.executionOrder ?? 0)
        })
    }, [sequentialCases])

    const handleDeleteCase = (caseId: string) => {
        const updatedCases = Object.entries(selectedCases).reduce((acc, [suiteId, cases]) => {
            const filtered = cases.filter((c: ICaseWithExecution) => c.id !== caseId)

            if (filtered.length > 0) {
                acc[suiteId] = filtered
            }

            return acc
        }, {} as Record<string, ICaseWithExecution[]>)

        setSelectedCases(updatedCases)

        const suitesWithCases = new Set(Object.keys(updatedCases))

        setSelectedSuites(selectedSuiteId.filter((id) => suitesWithCases.has(id)))
    }

    const handleAddSequentialCases = () => {
        setExecutionMode(EExecutionMode.SEQUENTIAL)
        setStep(2)
    }

    const handleDragEnd = (event: DragEndEvent) => {
        const { active, over } = event

        if (active.id !== over?.id) {
            const oldIndex = sortedSequentialCases.findIndex((c) => c.id === active.id)
            const newIndex = sortedSequentialCases.findIndex((c) => c.id === over?.id)
            
            if (oldIndex === -1 || newIndex === -1) return

            const newOrder = [...sortedSequentialCases]
            const [movedItem] = newOrder.splice(oldIndex, 1)

            newOrder.splice(newIndex, 0, movedItem)
            
            const updatedCasesWithOrder = newOrder.map((c, idx) => ({
                ...c,
                executionOrder: idx
            }))
            
            const newSelectedCases = cloneDeep(selectedCases)
            
            const orderMap = new Map(updatedCasesWithOrder.map((c) => [c.id, c.executionOrder]))
            
            Object.keys(newSelectedCases).forEach((suiteId) => {
                newSelectedCases[suiteId] = newSelectedCases[suiteId].map((c) => {
                    if (c.executionMode === EExecutionMode.SEQUENTIAL && orderMap.has(c.id)) {
                        return { ...c, executionOrder: orderMap.get(c.id) }
                    }

                    return c
                })
            })
            
            setSelectedCases(newSelectedCases)
        }
    }

    const handleClearSequentialCases = () => {
        // Filter out all sequential cases
        const updatedCases = Object.entries(selectedCases).reduce((acc, [suiteId, cases]) => {
            const filtered = cases.filter((c: ICaseWithExecution) => c.executionMode !== 'sequential')

            if (filtered.length > 0) {
                acc[suiteId] = filtered
            }

            return acc
        }, {} as Record<string, ICaseWithExecution[]>)

        setSelectedCases(updatedCases)

        const suitesWithCases = new Set(Object.keys(updatedCases))

        setSelectedSuites(selectedSuiteId.filter((id) => suitesWithCases.has(id)))
    }

    const sortedIds = map(sortedSequentialCases, 'id')

    const title = (
        <Flex align="center" gap={ 8 }>
            <OrderedListOutlined style={ { color: '#52c41a' } } />
            <span>{t('create_run.sequential_cases')}</span>
            <Badge
                count={ sequentialCasesCount }
                showZero
                style={ { backgroundColor: sequentialCasesCount > 0 ? '#52c41a' : '#d9d9d9' } }
            />
        </Flex>
    )

    const extra = (
        <Space size={ 4 }>
            <Button
                icon={ <PlusOutlined /> }
                onClick={ handleAddSequentialCases }
                size="small"
                type="link"
            >
                {'Add'}
            </Button>
            {sequentialCasesCount > 0 && (
                <Button
                    icon={ <DeleteOutlined /> }
                    onClick={ handleClearSequentialCases }
                    size="small"
                    type="link"
                    danger
                >
                    {'Clear'}
                </Button>
            )}
        </Space>
    )

    if (sequentialCasesCount === 0) {
        return (
            <Card extra={ extra } size="small" title={ title }>
                <Empty
                    description={ t('create_run.no_sequential_cases') }
                    image={ Empty.PRESENTED_IMAGE_SIMPLE }
                    style={ { margin: '8px 0' } }
                />
            </Card>
        )
    }

    const listHeight = Math.min(sequentialCasesCount * ITEM_HEIGHT, 280)

    return (
        <Card extra={ extra } size="small" title={ title }>
            <DndContext 
                onDragEnd={ handleDragEnd } 
                sensors={ sensors }
            >
                <SortableContext 
                    items={ sortedIds } 
                    strategy={ verticalListSortingStrategy }
                >
                    <VirtualList
                        data={ sortedSequentialCases }
                        height={ listHeight }
                        itemHeight={ ITEM_HEIGHT }
                        itemKey="id"
                    >
                        {(caseItem, index) => (
                            <SortableItem
                                key={ caseItem.id }
                                id={ caseItem.id }
                                index={ index }
                                item={ caseItem }
                                onDelete={ handleDeleteCase }
                            />
                        )}
                    </VirtualList>
                </SortableContext>
            </DndContext>
        </Card>
    )
}
