import { ArrowLeftOutlined, ArrowRightOutlined } from '@ant-design/icons';
import { useThemeToken } from '@Common/hooks';
import { useRunningStore } from '@Pages/RunningCase/store';
import { isNotUntestedLocalCreated } from '@Pages/RunningCase/utils/isNotUntestedStep.ts';
import { Button, Flex } from 'antd';
import size from 'lodash/size';

export const Stepper = () => {
    const token = useThemeToken()

    const run = useRunningStore((state) => state.currentRun)
    const setSelectedStep = useRunningStore((state) => state.setSelectedStep)
    const selected = useRunningStore((state) => state.selectedStep)

    const steps = run?.steps?.filter((item) => isNotUntestedLocalCreated(item)) || []
    const selectedIndex = steps.findIndex((item) => item?.localUUID! === selected?.id)
    const stepsSize = size(steps)

    const isPrevDisabled = selectedIndex === 0 || stepsSize === 0
    const isNextDisabled = (selectedIndex === steps.length - 1) || stepsSize === 0
    const currentSelectedStepIndex = run?.steps?.findIndex((item) => item.localUUID === selected?.id)

    const stepperInfo = (typeof currentSelectedStepIndex === 'undefined') ?
        null : `${currentSelectedStepIndex + 1} / ${size(run?.steps)}`

    const handleNext = () => {
        if (isNextDisabled) return
        const nextStep = steps[selectedIndex + 1]

        setSelectedStep(nextStep.localUUID!, nextStep, true)
    }

    const handlePrev = () => {
        if (isPrevDisabled) return
        const prevStep = steps[selectedIndex - 1]

        setSelectedStep(prevStep.localUUID!, prevStep, true)
    }

    return (
        <Flex
            align={ 'center' }
            gap={ 8 }
            style={ {
                height: 'fit-content',
                bottom: 24,
                zIndex: 2,
                position: 'absolute',
                left: '50%',
                transform: 'translateX(-50%)'
            } }
        >
            <Button
                disabled={ isPrevDisabled }
                icon={ <ArrowLeftOutlined/> }
                onClick={ handlePrev }
                style={ { borderRadius: '50%', background: token.colorWhite, boxShadow: token.boxShadowSecondary } }
                type={ 'text' }
            />
            {stepperInfo && (
                <Flex
                    style={ {
                        padding: '4px 12px',
                        borderRadius: 24,
                        background: token.colorWhite,
                        boxShadow: token.boxShadowSecondary
                    } }>
                    {stepperInfo}
                </Flex>
            )}
            <Button
                disabled={ isNextDisabled }
                icon={ <ArrowRightOutlined/> }
                onClick={ handleNext }
                style={ { borderRadius: '50%', background: token.colorWhite, boxShadow: token.boxShadowSecondary } }
                type={ 'text' }/>
        </Flex>
    )
}
