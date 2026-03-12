import { ArrowLeftOutlined, ArrowRightOutlined } from '@ant-design/icons';
import { useThemeToken } from '@Common/hooks';
import { useTestCaseStore } from '@Entities/test-case';
import { useChangeCase } from '@Pages/Runs/entities/Details/hooks';
import { useGroupedRunStore } from '@Pages/Runs/entities/Details/store';
import { Button, Flex } from 'antd';
import findIndex from 'lodash/findIndex';
import values from 'lodash/values';

export const ChangeCaseControls = () => {
    const flatSuites = useGroupedRunStore((state) => state.flatSuites)
    const token = useThemeToken()

    const cases = values(flatSuites)?.flat()

    const setCaseId = useChangeCase()

    const currentCase = useTestCaseStore((state) => state.currentCase)
    const currentCaseIndex = findIndex(cases, { case_id: currentCase?.case_id })

    const handleNextCase = () => {
        const nextIndex = currentCaseIndex + 1
        const nextCase = nextIndex === cases.length ? cases[0] : cases[nextIndex]
        const nextId = nextCase?.group_run_case_id

        if (!nextId) {
            return
        }

        setCaseId(nextId)
    }

    const handlePrevCase = () => {
        const prevIndex = currentCaseIndex - 1
        const prevCase = prevIndex < 0 ? cases[cases.length - 1] : cases[prevIndex]
        const prevId = prevCase?.group_run_case_id

        if (!prevId) {
            return
        }

        setCaseId(prevId)
    }
    
    const btnStyles = {
        borderRadius: '50%',
        background: token.colorWhite,
        boxShadow: token.boxShadowSecondary
    }

    const isPrevDisabled = currentCaseIndex === 0
    const isNextDisabled = currentCaseIndex === cases.length - 1

    return (
        <Flex
            gap={ 8 }
            style={ {
                left: '50%',
                width: 'fit-content',
                transform: 'translateX(-50%)',
                position: 'absolute',
                bottom: 16,
                zIndex: 999
            } }>
            <Button
                disabled={ isPrevDisabled }
                icon={ <ArrowLeftOutlined/> }
                onClick={ handlePrevCase }
                style={ btnStyles }
                type={ 'text' }
            />
            <Flex
                align={ 'center' }
                justify={ 'center' }
                style={ {
                    background: token.colorBgBase,
                    borderRadius: '500px',
                    padding: '4px 16px',
                    boxShadow: token.boxShadowSecondary
                } }
            >

                {currentCaseIndex + 1} / {cases.length}
            </Flex>
            <Button
                disabled={ isNextDisabled }
                icon={ <ArrowRightOutlined/> }
                onClick={ handleNextCase }
                style={ btnStyles }
                type={ 'text' }
            />
        </Flex>
    )
}
