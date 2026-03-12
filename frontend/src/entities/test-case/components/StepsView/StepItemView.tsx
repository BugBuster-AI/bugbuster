import { METHOD_COLORS } from '@Common/consts';
import { CLASSNAMES } from '@Common/consts/css.ts';
import { getCurlObj } from '@Common/utils';
import { renderStringWithVariables } from '@Common/utils/formatVariable.tsx';
import { parseVariablesInStep } from '@Common/utils/parseVariablesInStep.tsx';
import { IRunStep } from '@Entities/runs/models';
import { EStepType } from '@Entities/test-case/components/Form/models.ts';
import { ApiStepDetails } from '@Entities/test-case/components/StepsView/components/ApiStepDetails.tsx';
import { DefaultStepDetails } from '@Entities/test-case/components/StepsView/components/DefaultStepDetails.tsx';
import { ILocalStepData } from '@Entities/test-case/models';
import { Flex, Typography } from 'antd';
import cn from 'classnames';
import { CSSProperties, ReactNode } from 'react';
import { removeSlashes } from 'slashes';


export enum ELocalStepItemVariant {
    SIMPLE = 'simple',
    DETAILED = 'detailed'
}

interface IProps extends Omit<ILocalStepData, 'description'> {
    style?: CSSProperties
    disabled?: boolean
    description?: string | ReactNode
    variant?: ELocalStepItemVariant
    originalStep?: IRunStep
}

const getStepInfo = (step: ILocalStepData) => {
    const parsedValue = parseVariablesInStep({
        extra: step.extra || undefined,
        value: removeSlashes(step.name || '')
    })

    if (step.type === EStepType.API) {
        const curlObj = getCurlObj(parsedValue)
        const method = curlObj?.method?.toUpperCase()
        const methodComponent = method
            ? <Typography.Text style={ { fontWeight: 700, color: METHOD_COLORS[method] } }>{method}</Typography.Text>
            : null

        const urlRender = renderStringWithVariables(curlObj?.raw_url || parsedValue)

        return {
            title: <>{methodComponent} {urlRender}</>
        }
    }

    return {
        title: <>{renderStringWithVariables(parsedValue)}</>
    }
}

export const LocalStepItem = ({
    style: overrideStyle,
    disabled,
    variant,
    ...step
}: IProps) => {
    const disabledStyles = disabled ? {
        opacity: 0.5,
        cursor: 'not-allowed'
    } : {}

    const { title } = getStepInfo(step)

    let Details

    switch (step.type) {
        case EStepType.API:
            Details = <ApiStepDetails step={ { ...step } }/>
            break
        default:
            Details = <DefaultStepDetails step={ step } variant={ variant }/>
            break
    }

    return (
        <Flex
            align="flex-start"
            gap={ 16 }
            style={ {
                height: 'fit-content',
                // ...styles,
                ...overrideStyle,
                ...disabledStyles,
                width: '100%',
            } }
        >
            <Flex
                align="flex-start"
                flex={ 1 }
                gap={ 8 }
                justify="space-between"
                style={ { height: '100%', width: '100%', } }
                vertical
            >
                <Typography.Text
                    className={ cn(CLASSNAMES.testCaseStepName, CLASSNAMES.stepType(step?.type), 'step-name') }
                >
                    {title}
                </Typography.Text>

                {Details}

            </Flex>
        </Flex>
    )

}
