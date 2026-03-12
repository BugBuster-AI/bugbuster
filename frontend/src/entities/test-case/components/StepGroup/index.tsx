import { StatusIndicator } from '@Common/components';
import { METHOD_COLORS } from '@Common/consts';
import { CLASSNAMES } from '@Common/consts/css.ts';
import { IStep } from '@Common/types';
import { getCurlObj } from '@Common/utils';
import { renderStringWithVariables } from '@Common/utils/formatVariable.tsx';
import { EStepType } from '@Entities/test-case/components/Form/models.ts';
import { Divider, Flex, Typography } from 'antd';
import cn from 'classnames';
import map from 'lodash/map';
import size from 'lodash/size';
import { ReactElement } from 'react';

interface IProps {
    name: string;
    steps: IStep[]
}

const getValue = (step: IStep) => {
    if (step.type === EStepType.API) {
        const readyApiData = step?.apiData

        if (readyApiData?.url && readyApiData?.method) {
            const method = readyApiData.method.toUpperCase()
            const methodComponent = method
                ? <Typography.Text style={ { fontWeight: 700, color: METHOD_COLORS[method] } }>
                    {method}
                </Typography.Text>
                : null

            return <> {methodComponent} {renderStringWithVariables(readyApiData.url, true)} </>
        }
        const parsed = getCurlObj(step.step)

        // Если apiData уже есть, значит curl был отредактирован через форму (новый формат)

        const url = parsed?.raw_url
        const method = parsed?.method?.toUpperCase()

        const methodComponent = method
            ? <Typography.Text style={ { fontWeight: 700, color: METHOD_COLORS[method] } }>{method}</Typography.Text>
            : null

        return url ? <>{methodComponent} {renderStringWithVariables(url, true)}</> : step.step
    }

    return <>{renderStringWithVariables(step.step, true)}</>
}

export const StepGroup = ({ steps, name }: IProps): ReactElement | null => {
    if (!size(steps)) return null

    return (
        <Flex gap={ 16 } vertical>
            <Divider orientation="left" orientationMargin={ 0 } style={ { marginBottom: 0 } } plain>
                <Typography.Title level={ 5 }>{name}</Typography.Title>
            </Divider>

            {map(steps, (item, index) => {

                return (
                    <Flex key={ `testCase-stepItem-${index}` } align={ 'flex-start' } gap={ 16 }>
                        <StatusIndicator
                            count={ index + 1 }
                            type={ item.type }
                        />
                        <Typography.Text
                            className={ cn(CLASSNAMES.testCaseStepName, CLASSNAMES.stepType(item?.type)) }
                        >
                            {getValue(item)}
                        </Typography.Text>
                    </Flex>
                )
            })}
        </Flex>
    )
}
