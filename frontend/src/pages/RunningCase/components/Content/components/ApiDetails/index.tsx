import { StatusLabel } from '@Components/StatusLabel';
import { formatCurl } from '@Entities/test-case/components/Form/components/ApiInput/helper.ts';
import { EStepType } from '@Entities/test-case/components/Form/models';
import { ImageTag } from '@Pages/RunningCase/components/Content/components/ImageTag.tsx';
import { InfoBlock } from '@Pages/RunningCase/components/Content/components/InfoBlock.tsx';
import { useRunningStore } from '@Pages/RunningCase/store';
import { Flex, Image } from 'antd';
import cn from 'classnames';
import entries from 'lodash/entries';
import isArray from 'lodash/isArray';
import isEmpty from 'lodash/isEmpty';
import isObject from 'lodash/isObject';
import isString from 'lodash/isString';
import map from 'lodash/map';
import size from 'lodash/size';
import { memo, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import SyntaxHighlighter from 'react-syntax-highlighter';
import { docco } from 'react-syntax-highlighter/dist/esm/styles/hljs';
import { removeSlashes } from 'slashes';
import styles from './ApiDetails.module.scss'

export const ApiDetails = memo(() => {

    const selectedStep = useRunningStore((state) => state.selectedStep)?.step
    const stepExtra = selectedStep?.extra
    const setVariables = stepExtra?.set_variables
    const variablesStore = stepExtra?.variables_store

    const { t } = useTranslation()

    const safeStringifyValue = (value?: unknown) => {
        if (!value) return ''
        try {
            if (isArray(value)) {
                if (size(value) === 0) {
                    return '[]'
                }

                return JSON.stringify(value, null, 2)
            }
            if (isObject(value)) {
                if (isEmpty(value)) {
                    return ''
                }

                return JSON.stringify(value, null, 2)
            }

            if (isString(value)) {
                return value
            }

            return JSON.stringify(value, null, 2)
        } catch {
            return JSON.stringify(value, null, 2)
        }
    }

    const requestBody = useMemo(() => {
        try {
            const { obj } = formatCurl(stepExtra?.value || '') || {}
            const body = obj?.data || obj.files

            return safeStringifyValue(body)
        } catch {
            return null
        }
    }, [stepExtra])

    const isExpectedResult = selectedStep?.step_type === EStepType.RESULT

    const stringifyResponse =
        useMemo(() => (stepExtra?.api_response ? safeStringifyValue(stepExtra?.api_response) : null), [stepExtra])

    const before = selectedStep?.before_annotated_url
    const after = selectedStep?.after
    
    return (
        <>
            {isExpectedResult && Boolean(before) && (
                <Flex vertical>
                    <ImageTag>
                        {t('running_page.buttons.before')}
                    </ImageTag>

                    <Image src={ before?.url }/>
                </Flex>
            )}
            {isExpectedResult && Boolean(after) && (
                <Flex vertical>
                    <ImageTag>
                        {t('running_page.buttons.after')}
                    </ImageTag>

                    <Image src={ after?.url }/>
                </Flex>
            )}
            <InfoBlock
                content={ stepExtra?.api_status_code?.toString() }
                title={ t('running_page.apiStep.statusCode') }
            />
            {size(stepExtra?.validations_log) > 0 && <InfoBlock
                title={ t('running_page.apiStep.validations') }
            >
                <Flex gap={ 16 } vertical>
                    {map(stepExtra?.validations_log, (log, index) => {
                        return <StatusLabel key={ `validation-log-${index}` } title={ log } checkStatusInTitle/>
                    })}
                </Flex>
            </InfoBlock>}
            <InfoBlock
                content={ removeSlashes(stepExtra?.value || '') }
                contentClass={ styles.processedCommand }
                title={ t('running_page.apiStep.processedCommand') }
            />
            {requestBody && !isEmpty(requestBody) && <InfoBlock
                className={ styles.highlighterWrapper }
                content={ requestBody }
                title={ t('running_page.apiStep.apiRequest') }
            >
                <SyntaxHighlighter className={ styles.highlighter } style={ docco } wrapLongLines>
                    {requestBody}
                </SyntaxHighlighter>
            </InfoBlock>}
            {!isEmpty(setVariables) && (
                <InfoBlock
                    title={ t('running_page.apiStep.setVariables') }
                >
                    <Flex vertical>
                        {map(entries(setVariables), ([key, value], index) => {
                            return (
                                <p
                                    key={ `variable-set-item-${index}` }
                                    style={ { marginBlock: 0 } }
                                >
                                    {key} = {value}
                                </p>
                            )
                        })}
                    </Flex>
                </InfoBlock>
            )}
            {!isEmpty(variablesStore) && (
                <InfoBlock
                    title={ t('running_page.apiStep.variablesStore') }
                >
                    <Flex vertical>
                        {map(entries(variablesStore), ([key, value], index) => {
                            return (
                                <p
                                    key={ `variable-set-item-${index}` }
                                    style={ { marginBlock: 0 } }
                                >
                                    {key} = {JSON.stringify(value, null, 4)}
                                </p>
                            )
                        })}
                    </Flex>
                </InfoBlock>
            )}
            {!!stringifyResponse && <InfoBlock
                className={ styles.highlighterWrapper }
                title={ t('running_page.apiStep.apiResponse') }
            >
                <SyntaxHighlighter
                    className={ cn(styles.highlighter, styles.apiResponse) }
                    language={ 'json' }
                    style={ docco }
                    wrapLongLines>
                    {stringifyResponse}
                </SyntaxHighlighter>
            </InfoBlock>}
        </>
    )
})
