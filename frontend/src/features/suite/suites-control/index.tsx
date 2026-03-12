import { BaseLayout } from '@Common/components';
import { DragCaseEvents, DragOverTypes } from '@Common/consts';
import { useThemeToken } from '@Common/hooks';
import { asyncHandler } from '@Common/utils';
import { DndContext, DragEndEvent, pointerWithin } from '@dnd-kit/core';
import { SuitesTreeList } from '@Entities/suite';
import { useSuiteStore } from '@Entities/suite/store';
import { useUpdateTestCase } from '@Entities/test-case/queries';
import { IMovingCase, SuitesControlContext } from '@Features/suite/suites-control/context';
import { Flex, Splitter } from 'antd';
import isNil from 'lodash/isNil';
import isString from 'lodash/isString';
import { ReactElement, useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { RightSide } from './components';
import { SuiteTree } from '../suite-tree';

const DEFAULT_WIDTH = [320]
const WIDTH_KEY = 'suitePanelWidth'

export const SuitesControl = (): ReactElement => {
    const storageWidth = localStorage.getItem(WIDTH_KEY)
    const [movingCaseToSuite, setMovingCaseToSuite] = useState<IMovingCase | undefined>(undefined)
    const setHoveredSuiteId = useSuiteStore((state) => state.setHoveredSuiteId)
    const setSelectedSuite = useSuiteStore((state) => state.setSuite)
    const { id: projectId } = useParams()
    const asyncUpdateTestCase = useUpdateTestCase()

    const getInitialWidth = () => {
        try {
            if (storageWidth) {
                return JSON.parse(storageWidth)
            }

            return DEFAULT_WIDTH
        } catch {
            localStorage.removeItem(WIDTH_KEY)

            return DEFAULT_WIDTH
        }

    }

    const [sizes, setSizes] = useState<(number | string)[]>(getInitialWidth());
    const token = useThemeToken()

    const handleResizeEnd = (width: number[]) => {
        localStorage.setItem(WIDTH_KEY, JSON.stringify(width))
    }

    const onDragEnd = async (e: DragEndEvent) => {
        const { active, over } = e || {}

        setHoveredSuiteId(undefined)

        if (over) {
            const data = over.data.current

            if (data?.overType === DragOverTypes.SUITE) {
                const newSuiteId = over?.id
                const prevSuiteId = active?.data?.current?.suite_id
                const caseId = active?.data?.current?.case_id

                if (isString(newSuiteId) && prevSuiteId !== newSuiteId && !isNil(caseId)) {
                    setMovingCaseToSuite({
                        case_id: caseId,
                        suite_id: newSuiteId
                    })

                    await asyncHandler(asyncUpdateTestCase.mutateAsync.bind(null, {
                        case_id: caseId,
                        suite_id: newSuiteId as string
                    }), {
                        onFinally: () => {

                            setMovingCaseToSuite(undefined)
                        }
                    })

                }
            }
        }

        const event = new CustomEvent(DragCaseEvents.DRAG_END, {
            detail: e
        })


        window.dispatchEvent(event);
    }

    const memoizedValue = useMemo(() => ({
        movingCaseToSuite,
        setMovingCaseToSuite
    }), [movingCaseToSuite])

    useEffect(() => {
        setSelectedSuite(null)
    }, [projectId]);

    return (
        <SuitesControlContext.Provider value={ memoizedValue }>
            <BaseLayout style={ { paddingBottom: 0 } }>
                <Flex flex={ 1 } gap={ token.marginLG }>
                    <DndContext
                        collisionDetection={ pointerWithin }
                        onDragEnd={ onDragEnd }
                    >
                        <Splitter onResize={ setSizes } onResizeEnd={ handleResizeEnd }>
                            <Splitter.Panel max={ 560 } min={ 280 } size={ sizes[0] }>
                                <SuitesTreeList
                                    treeSlot={ <SuiteTree suiteChanging={ movingCaseToSuite?.suite_id }/> }
                                />
                            </Splitter.Panel>

                            <Splitter.Panel size={ sizes[1] } style={ { paddingLeft: '20px' } }>
                                <RightSide/>
                            </Splitter.Panel>
                        </Splitter>
                    </DndContext>
                </Flex>
            </BaseLayout>
        </SuitesControlContext.Provider>
    )
}
