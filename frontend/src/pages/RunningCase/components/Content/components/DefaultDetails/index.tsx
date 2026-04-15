import { RunErrorText } from '@Common/components/RunErrorText';
import { ERunStatus } from '@Entities/runs/models';
import { isShowBeforeImage } from '@Entities/runs/utils/isShowBeforeImage';
import { TestCaseApi } from '@Entities/test-case/api';
import { EStepType } from '@Entities/test-case/components/Form/models.ts';
import { codegenHighlightUidFromRunStep } from '@Features/test-case/playwright-codegen/codegenHighlightUid';
import { extractCodegenSnippetForStep } from '@Features/test-case/playwright-codegen/extractCodegenSnippet';
import { ImageTag } from '@Pages/RunningCase/components/Content/components/ImageTag.tsx';
import { InfoBlock } from '@Pages/RunningCase/components/Content/components/InfoBlock.tsx';
import { getFormattedActionPlan } from '@Pages/RunningCase/components/Content/helper.ts';
import { useRunningStore } from '@Pages/RunningCase/store';
import { useQuery } from '@tanstack/react-query';
import { Flex, Image, Typography } from 'antd';
import find from 'lodash/find';
import get from 'lodash/get';
import isEmpty from 'lodash/isEmpty';
import isNil from 'lodash/isNil';
import { useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { ClickAreaCanvas, EditClickAreaControls } from './components';
import { RunningStepSyntaxBlock } from './RunningStepSyntaxBlock';
import { isShowAfterImage } from '../../../../../../entities/runs/utils/isShowBeforeImage';

const caseApi = TestCaseApi.getInstance();

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

    const isCodeExecution = run?.execution_engine === 'playwright_js';
    const caseIdForArtifact =
        run?.case?.case_id != null ? String(run.case.case_id) : null;
    const playwrightArtifactId = run?.playwright_codegen_artifact_id ?? null;

    const { data: runCodegenArtifact } = useQuery({
        queryKey: [
            'playwright-codegen-artifact-by-id',
            caseIdForArtifact,
            playwrightArtifactId,
        ],
        queryFn: () =>
            caseApi.getPlaywrightCodegenArtifactById(
                caseIdForArtifact!,
                playwrightArtifactId!,
            ),
        enabled: Boolean(
            isCodeExecution && caseIdForArtifact && playwrightArtifactId,
        ),
    });

    const codeSnippetForStep = useMemo(() => {
        if (!runCodegenArtifact || !step) {
            return null;
        }
        const stepUid = codegenHighlightUidFromRunStep(step, run?.case);

        return extractCodegenSnippetForStep(
            runCodegenArtifact.source_code,
            runCodegenArtifact.step_spans,
            stepUid,
        );
    }, [runCodegenArtifact, step, run?.case]);

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
    // Code run: при FAILED действие не выполнено — только before (не показываем after, в т.ч. из старых данных).
    const needShowAfter =
        isShowAfterImage(step, { isEditing }) &&
        !(isCodeExecution && step?.status_step === ERunStatus.FAILED)

    const needsBottomPaddingForStepper =
        (!hasValidationResult &&
            ((isCodeExecution && !!codeSnippetForStep) ||
                (!isCodeExecution && !!stepActionPlan))) ||
        Boolean(step?.validation_result?.reflection_thoughts)

    const showStepError = Boolean(step?.comment?.trim())

    return (
        <Flex style={ { paddingBottom: needsBottomPaddingForStepper ? 88 : 0, width: '100%' } } vertical>
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
                    {showStepError && (
                        <InfoBlock
                            first={ true }
                            title={ t('running_page.step_error_title') }
                        >
                            <Typography.Text
                                style={ {
                                    display: 'block',
                                    maxHeight: 142,
                                    overflow: 'auto',
                                } }
                            >
                                <RunErrorText text={ step?.comment?.trim() || '' } />
                            </Typography.Text>
                        </InfoBlock>
                    )}
                    <InfoBlock
                        content={ step?.validation_result?.reflection_title }
                        first={ !showStepError }
                        title={ t('running_page.expected') }
                    />

                    {!hasValidationResult && (
                        <InfoBlock
                            content={ step?.step_description }
                            title={ t('running_page.prompt') }
                        />
                    )}

                    {!hasValidationResult && isCodeExecution && codeSnippetForStep && (
                        <InfoBlock title={ t('running_page.code') }>
                            <RunningStepSyntaxBlock
                                code={ codeSnippetForStep }
                                language="javascript"
                            />
                        </InfoBlock>
                    )}

                    {!hasValidationResult && !isCodeExecution && stepActionPlan && (
                        <InfoBlock title={ t('running_page.action_plan') }>
                            <RunningStepSyntaxBlock
                                code={ stepActionPlan }
                                language="json"
                            />
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
        </Flex>
    );
};
