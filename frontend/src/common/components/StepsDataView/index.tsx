import { EStatusIndicator, StatusIndicator, StepGroup } from '@Common/components';
import { DEFAULT_IMAGE_SIZE } from '@Common/consts';
import { groupSteps } from '@Common/utils';
import { getRunStatusToIndicator } from '@Common/utils/common.ts';
import { parseVariablesInStep } from '@Common/utils/parseVariablesInStep.tsx';
import { StepAccordion } from '@Components/StepAccordion';
import { LogCard } from '@Entities/runs/components/LogCard';
import { ERunStatus, IRunById, IRunStep, TStepGroup } from '@Entities/runs/models';
import { convertStepType } from '@Entities/runs/utils/stepType.ts';
import { Flex, Image, Result, Steps } from 'antd';
import entries from 'lodash/entries';
import find from 'lodash/find';
import includes from 'lodash/includes';
import map from 'lodash/map';
import size from 'lodash/size';
import { Fragment, memo, ReactNode, useMemo } from 'react';
import { useTranslation } from 'react-i18next';

interface IRenderLogProps {
    step: IRunStep
    status: EStatusIndicator
    isLoading: boolean
    index: number
    stepInFocus: boolean
}

interface IProps {
    showFinishState?: boolean
    run?: IRunById
    renderGroup?: ({ label, noLabel }: { label: string, noLabel?: boolean }) => ReactNode
    renderLog?: (props: IRenderLogProps) => ReactNode
    noGroup?: boolean
    withAttachments?: boolean
    topSlot?: ReactNode
    error?: string
    needAllExpected?: boolean
}

const IN_PROGRESS_STATUSES = [ERunStatus.IN_PROGRESS, ERunStatus.IN_QUEUE, ERunStatus.RETEST]

// TODO: Устаревший компонент, переехать на RunStepsView и useLocalStepData
export const StepsDataView = memo(({
    topSlot,
    run,
    renderGroup,
    withAttachments,
    error,
    renderLog,
    noGroup = false,
}: IProps) => {
    const { t } = useTranslation()
    const runStatus = run?.status
    const steps = run?.steps || []

    const groupedSteps = useMemo(() => {
        if (noGroup) {
            return { step: steps } as Record<TStepGroup, IRunStep[]>
        }

        return groupSteps(steps)
    }, [run, noGroup])

    const loadingStep = find(steps, ['status_step', ERunStatus.UNTESTED])

    if (!!error) {
        return <Result status={ 'error' } title={ error }/>
    }

    return (

        <Flex vertical>
            {topSlot}
            {withAttachments && size(run?.attachments) > 0 &&
                <Flex>
                    <StepAccordion
                        defaultOpened={ false }
                        label={ t('group_run.drawer.attachments') }
                        style={ { width: '100%' } }>

                        <div style={ { width: '100%', overflow: 'hidden' } }>
                            <Flex gap={ 8 } style={ { overflow: 'auto' } }>
                                {run?.attachments?.map((attachment, index) => (
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

            {map(entries(groupedSteps), ([key, value]: [key: TStepGroup, value: IRunStep[]], index: number) => {
                if (!size(value)) return null

                const GroupView = renderGroup || StepGroup

                return (
                    <GroupView
                        key={ `step-group-info-${index}-${key}` }
                        label={ t(`group_steps.${key}`) }
                        noLabel={ noGroup }>

                        {value.map((step, index) => {
                            const isLoading = loadingStep?.index_step === step.index_step
                                    && includes(IN_PROGRESS_STATUSES, runStatus)

                            const status = getRunStatusToIndicator(step.status_step)

                            if (renderLog) {
                                return (
                                    <Fragment key={ `step-item-${key}-${index}` }>
                                        {renderLog({ step, stepInFocus: isLoading, status, isLoading, index })}
                                    </Fragment>
                                )
                            }

                            const stepName = step.extra ? parseVariablesInStep({
                                value: step.original_step_description || '',
                                extra: step.extra
                            }) : step.original_step_description

                            const title =
                                <LogCard
                                    afterImg={ step?.after?.url }
                                    attachments={ step?.attachments }
                                    beforeImg={ step?.before_annotated_url?.url }
                                    description={ step?.comment }
                                    isLoading={ true }
                                    time={ false }
                                    title={ stepName }
                                    variant={ 'history' }
                                    noStatus
                                />

                            return (
                                <Fragment key={ `step-item-${key}-${index}` }>
                                    <Steps.Step
                                        icon={
                                            <StatusIndicator
                                                badgeStyle={ { display: 'inline' } }
                                                className={ 'step-indicator' }
                                                count={ step.part_num }
                                                loading={ isLoading }
                                                status={ status }
                                                type={ convertStepType(step.step_type, true) }
                                            />
                                        }
                                        status={ 'wait' }
                                        style={ { paddingBottom: 16 } }
                                        title={ title }
                                    />
                                </Fragment>
                            )
                        })}
                    </GroupView>
                )
            }
            )}
        </Flex>
    )
})
