import { isShowBeforeImage } from '@Entities/runs/utils/isShowBeforeImage';
import { EStepType } from '@Entities/test-case/components/Form/models.ts';
import { ImageTag } from '@Pages/RunningCase/components/Content/components/ImageTag.tsx';
import { InfoBlock } from '@Pages/RunningCase/components/Content/components/InfoBlock.tsx';
import { getFormattedActionPlan } from '@Pages/RunningCase/components/Content/helper.ts';
import { useRunningStore } from '@Pages/RunningCase/store';
import { Flex, Image, Typography } from 'antd';
import find from 'lodash/find';
import get from 'lodash/get';
import isEmpty from 'lodash/isEmpty';
import isNil from 'lodash/isNil';
import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { ClickAreaCanvas, EditClickAreaControls } from './components';
import { isShowAfterImage } from '../../../../../../entities/runs/utils/isShowBeforeImage';

export const DefaultDetails = () => {
    const selectedStep = useRunningStore((state) => state.selectedStep);
    const editingSteps = useRunningStore((state) => state.editingSteps);
    const run = useRunningStore((state) => state.currentRun);
    const currentEditingStep = find(
        editingSteps,
        (item) => item.id === selectedStep?.id,
    );
    const isEditing = !!currentEditingStep;

    const getStep = () => {
        
        /*
         * ??
         * if (selectedStep?.step?.checkResults) {
         *     return get(selectedStep, 'step', null);
         * }
         */
         
        if (isEditing) {
            return get(currentEditingStep, 'step', null);
        }

        return get(selectedStep, 'step', null);
    };
    // checkResults - появляется после сохранения кейса
    const step = getStep();
    const isExpectedResult = step?.step_type === EStepType.RESULT;
    const hasValidationResult = !isEmpty(step?.validation_result);

    const after = get(step, 'after', null);
    const stepActionPlan = !isNil(step?.index_step)
        ? getFormattedActionPlan(
            get(run, `case.action_plan.${[step?.index_step]}`),
            step?.step_type,
        )
        : undefined;

    const { t } = useTranslation();

    const originalBefore = get(step, 'before_annotated_url', null);
    const beforeAnnotated = get(currentEditingStep, 'step.before_annotated_url') || originalBefore;

    const before = get(step, 'before', null);

    const canEditClickArea = Boolean(beforeAnnotated) && !isExpectedResult;

    const isEditingClickArea = Boolean(currentEditingStep?.step?.editingClickArea);
    const hasClickAreaResponse = Boolean(currentEditingStep?.step?.editingClickArea?.hasResponse);
    const showStepInfo = !isEditingClickArea || hasClickAreaResponse;

    const BeforeImageContent = useCallback(() => {
        const showContextCoordinates = showStepInfo && currentEditingStep?.step?.contextScreenshotMode?.coordinates

        if (((isEditingClickArea && !hasClickAreaResponse && isEditing) && before?.url) || showContextCoordinates) {

            let url
 
            if (isExpectedResult) {
                url = before?.url || after?.url
            } else if (showContextCoordinates) {
                url = beforeAnnotated?.url
            } else {
                url = before?.url
            }
            
            return (
                <ClickAreaCanvas
                    disableDraw={ !!showContextCoordinates }
                    imageUrl={ url || '' }                
                />
            )
        }

        if (isExpectedResult) {
            return <Image src={ before?.url } />
        }

        return <Image src={ beforeAnnotated?.url } />
    }, [isEditingClickArea, showStepInfo, isExpectedResult, selectedStep?.id, isEditing])

    const needShowNotUsingContextScreenshot = 
        !selectedStep?.step?.extra?.context_screenshot_used 
        && selectedStep?.step?.extra?.context_screenshot_path
        && !isEditing 

    const needShowBefore = isShowBeforeImage(step, isExpectedResult ? before : beforeAnnotated)
    const needShowAfter = isShowAfterImage(step, { isEditing })

    return (
        <>
            {needShowNotUsingContextScreenshot && 
                <Typography style={ { marginBottom: 8 } }>{t('contextScreenshot.notUsing')}</Typography>
            }

            {canEditClickArea && <EditClickAreaControls />}

            {needShowBefore && (
                <Flex style={ { width: '100%' } } vertical>
                    <ImageTag>{t('running_page.buttons.before')}</ImageTag>

                    <BeforeImageContent />
                </Flex>
            )}
            {needShowAfter && (
                <Flex vertical>
                    <ImageTag>{t('running_page.buttons.after')}</ImageTag>

                    <Image src={ after?.url } />
                </Flex>
            )}
            {showStepInfo && (
                <>
                    <InfoBlock
                        content={ step?.validation_result?.reflection_title }
                        title={ t('running_page.expected') }
                        first
                    />

                    {!hasValidationResult && (
                        <InfoBlock
                            content={ step?.step_description }
                            title={ t('running_page.prompt') }
                        />
                    )}

                    {!hasValidationResult && stepActionPlan && (
                        <InfoBlock title={ t('running_page.action_plan') }>
                            <Typography style={ { whiteSpace: 'pre-wrap' } }>
                                {stepActionPlan}
                            </Typography>
                        </InfoBlock>
                    )}

                    {step?.validation_result?.reflection_thoughts && (
                        <InfoBlock title={ t('running_page.thoughts') }>
                            <p style={ { whiteSpace: 'pre-line' } }>
                                {step?.validation_result?.reflection_thoughts}
                            </p>
                        </InfoBlock>
                    )}
                </>
            )}
        </>
    );
};
