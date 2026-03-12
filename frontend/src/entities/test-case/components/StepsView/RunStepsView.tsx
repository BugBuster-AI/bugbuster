import { EStatusIndicator, StatusIndicator, StepGroup } from '@Common/components';
import { ResultContent } from '@Common/components/ResultCard';
import { DEFAULT_IMAGE_SIZE } from '@Common/consts';
import { useThemeToken } from '@Common/hooks';
import { isSharedStep } from '@Common/utils/test-case/consts.ts';
import { StepAccordion } from '@Components/StepAccordion';
import { ERunStatus, IMedia, TStepGroup } from '@Entities/runs/models';
import { EStepType } from '@Entities/test-case/components/Form/models.ts';
import { LocalStepItem } from '@Entities/test-case/components/StepsView/StepItemView.tsx';
import { ELocalStepStatus, ILocalStepData } from '@Entities/test-case/models';
import { Flex, Image, Result, Steps, Typography } from 'antd';
import entries from 'lodash/entries';
import map from 'lodash/map';
import size from 'lodash/size';
import { Fragment, ReactElement, ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

interface IProps {
    status?: ERunStatus
    steps: Record<TStepGroup, ILocalStepData[]>
    attachments?: IMedia[]
    grouping?: boolean
    renderStepCard?: (step: ILocalStepData) => ReactElement
    errorMessage?: string
    topSlot?: ReactNode
    summary?: string | null
}

const convertToStatusIndicator = (status?: ELocalStepStatus, isLoading?: boolean) => {
    if (isLoading) {
        return EStatusIndicator.LOADING
    }
    switch (status) {
        case ELocalStepStatus.SUCCESS:
            return EStatusIndicator.SUCCESS
        case ELocalStepStatus.FAILED:
            return EStatusIndicator.ERROR
        default:
            return EStatusIndicator.IDLE
    }
}

export const RunStepsView = ({
    steps,
    topSlot,
    attachments,
    status,
    errorMessage,
    grouping,
    summary,
    renderStepCard
}: IProps): ReactElement => {
    const { t } = useTranslation()
    const token = useThemeToken()

    if (!!errorMessage) {
        return <Result status={ 'error' } title={ errorMessage }/>
    }

    const getColor = () => {
        if (status === ERunStatus.PASSED) {
            return token.colorSuccess
        }
        if (status === ERunStatus.FAILED) {
            return token.colorError
        }

        return ''
    }

    const WrapComponent = !grouping ? Steps : Fragment
    const stepsWrapperProps = !grouping ? {
        direction: 'vertical',
        size: 'small'
    } : undefined

    return (
        <Flex vertical>
            {summary && (
                <ResultContent
                    style={ { color: getColor(), marginBottom: 16 } }
                    value={ summary }
                />
            )}
            {topSlot}
            {size(attachments) > 0 &&
                <Flex>
                    <StepAccordion
                        defaultOpened={ false }
                        label={ t('group_run.drawer.attachments') }
                        style={ { width: '100%' } }>

                        <div style={ { width: '100%', overflow: 'hidden' } }>
                            <Flex gap={ 8 } style={ { overflow: 'auto' } }>
                                {map(attachments, (attachment, index) => (
                                    <Image
                                        key={ `${index}-${attachment.file}` }
                                        src={ attachment?.url }
                                        style={ {
                                            objectFit: 'contain',
                                            height: '100%',
                                            minWidth: 'initial',
                                            width: 'auto'
                                        } }
                                        wrapperStyle={ {
                                            height: DEFAULT_IMAGE_SIZE.SMALL.height,
                                        } }
                                    />
                                ))}
                            </Flex>
                        </div>
                    </StepAccordion>
                </Flex>
            }
            {/*@ts-ignore*/}
            <WrapComponent { ...stepsWrapperProps }>
                {map(entries(steps), ([key, items]) => {
                    const children = map(items, (step) => {
                        if (!size(items)) return null

                        const description = step.type === EStepType.RESULT ?
                            <Flex gap={ 4 } vertical>
                                <Typography.Text
                                    type={ 'secondary' }
                                >
                                    {step.title || ''}
                                </Typography.Text>
                                <Typography.Text
                                    type={ 'secondary' }
                                >
                                    {step.description}
                                </Typography.Text>
                            </Flex> : step.description

                        const stepEl = <LocalStepItem 
                            { ...step }
                            description={ description }/>

                        return renderStepCard?.(step) || (
                            <Steps.Step
                                key={ `step-item-${step.partNum}` }
                                icon={
                                    <StatusIndicator
                                        className={ 'step-indicator' }
                                        count={ step.partNum }
                                        isSharedStep={ isSharedStep(step) }
                                        loading={ step.isLoading }
                                        status={ convertToStatusIndicator(step.status, step.isLoading) }
                                        type={ step.type }
                                    />
                                }
                                status={ 'wait' }
                                style={ { paddingBottom: 16 } }
                                title={ stepEl }
                            >
                            </Steps.Step>
                        )
                    })

                    if (grouping) {
                        return (
                            <StepGroup
                                key={ `step-group-${key}` }
                                label={ t(`group_steps.${key}`) }
                                loading={ false }
                            >
                                {children}
                            </StepGroup>
                        )
                    }

                    return children
                })
                }
            </WrapComponent>
        </Flex>
    )
}


