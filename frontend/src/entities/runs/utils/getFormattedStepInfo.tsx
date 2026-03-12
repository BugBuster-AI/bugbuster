import { METHOD_COLORS } from '@Common/consts';
import { getCurlObj } from '@Common/utils';
import { renderStringWithVariables } from '@Common/utils/formatVariable.tsx';
import { parseVariablesInStep } from '@Common/utils/parseVariablesInStep.tsx';
import { IRunStep } from '@Entities/runs/models';
import { EStepType } from '@Entities/test-case/components/Form/models.ts';
import { Typography } from 'antd';
import { ReactNode } from 'react';
import { removeSlashes } from 'slashes';

interface IOptions {
    fullValue?: boolean
    isExpectedValue?: boolean
    isRawValue?: boolean
    needMethodInApi?: boolean
    addResultVerificationMode?: boolean
}

export const getFormattedStepInfo = (step: IRunStep, {
    fullValue,
    isRawValue,
    needMethodInApi = true,
    addResultVerificationMode = true
}: IOptions = {}) => {
    const initialValue = step.original_step_description

    // если нужно сырое значение
    if (isRawValue) {
        const titleComponent = <>{renderStringWithVariables(initialValue || '', true)} </>

        return {
            title: initialValue,
            actionName: '',
            titleComponent: titleComponent
        }
    }

    const parsedValue = parseVariablesInStep({
        extra: step.extra || undefined,
        value: removeSlashes(initialValue || '')
    })

    // если нужно полное значение
    if (fullValue) {
        const titleComponent = <>{renderStringWithVariables(parsedValue)} </>

        return {
            title: parsedValue,
            actionName: '',
            titleComponent: titleComponent
        }
    }

    if (step.step_type === EStepType.API) {
        const initialUrl = step?.extra?.url
        const initialMethod = step?.extra?.method

        if (initialUrl && initialMethod) {
            const parsedUrl = parseVariablesInStep({
                extra: step.extra || undefined,
                value: removeSlashes(initialUrl || '')
            }, 'url')

            const method = needMethodInApi ? initialMethod?.toUpperCase() : null
            const methodComponent = method
                ? <Typography.Text style={ { fontWeight: 700, color: METHOD_COLORS[method] } }>
                    {method}
                </Typography.Text>
                : null
            const urlRender = renderStringWithVariables(parsedUrl)

            const titleComponent = <>{methodComponent} {urlRender}</>

            return {
                actionName: initialMethod,
                title: parsedUrl,
                titleComponent
            }
        }


        const curlObj = getCurlObj(parsedValue)
        const method = curlObj?.method?.toUpperCase()

        const methodComponent = method
            ? <Typography.Text style={ { fontWeight: 700, color: METHOD_COLORS[method] } }>{method}</Typography.Text>
            : null

        const urlRender = renderStringWithVariables(curlObj?.raw_url || parsedValue)

        const titleComponent = <>{methodComponent} {urlRender}</>

        return {
            actionName: curlObj?.method,
            title: curlObj?.raw_url || parsedValue,
            titleComponent
        }
    }

    let actionName: string | ReactNode = step.action

    if (step.step_type === EStepType.RESULT && addResultVerificationMode) {
        if (step.extra?.use_single_screenshot === true) {
            actionName = (
                <Typography.Text style={ { fontSize: '12px' } } type="secondary">
                    State verification
                </Typography.Text>
            )
        } else if (step.extra?.use_single_screenshot === false){
            actionName = (
                <Typography.Text style={ { fontSize: '12px' } } type="secondary">
                    Dynamic changes verification
                </Typography.Text>
            )
        } else {
            actionName = ''
        }
    }

    const titleComponent = <>{renderStringWithVariables(parsedValue)}</>

    return {
        actionName,
        title: parsedValue || initialValue,
        titleComponent
    }
}
