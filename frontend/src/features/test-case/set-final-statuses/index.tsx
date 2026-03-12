import { StatusBadge } from '@Common/components';
import { ERunStatus } from '@Entities/runs/models';
import { caseQueries } from '@Entities/test-case/queries';
import { useQuery } from '@tanstack/react-query';
import { Flex, Skeleton } from 'antd';
import map from 'lodash/map';
import { useState } from 'react';

interface IProps {
    onChange?: (item?: ERunStatus) => void
    value?: ERunStatus
    selectable?: boolean
    resettable?: boolean
}

export const SetFinalTestStatus = ({ onChange, selectable, value, resettable = true }: IProps) => {
    const [current, setCurrent] = useState<undefined | ERunStatus>(value)
    const { data, isLoading } = useQuery(caseQueries.finalTypes())

    const handleClick = (status: ERunStatus) => {

        if (current) {
            if (current === status && resettable) {
                setCurrent(undefined)
                onChange && onChange(undefined)

                return
            }
        }
        setCurrent(status)
        onChange && onChange(status)
    }

    return (
        <Flex align={ 'center' } gap={ 8 }>
            {isLoading && <Skeleton paragraph={ { rows: 0 } }/>}
            {map(data, (item) => {
                const isCurrent = item === current

                return (
                    <StatusBadge
                        key={ `allStatuses-${item}` }
                        inverted={ isCurrent && selectable }
                        onClick={ handleClick.bind(null, item) }
                        status={ item }
                    />
                )
            }
            )}
        </Flex>
    )
}
