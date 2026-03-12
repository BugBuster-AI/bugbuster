import { ErrorCard } from '@Features/records/show-record/components/ErrorCard';
import { useShowRecordStore } from '@Features/records/show-record/store';
import { Flex, Skeleton, Steps, Tabs, Typography } from 'antd';
import get from 'lodash/get';
import map from 'lodash/map';
import size from 'lodash/size';
import styles from './StepInfo.module.scss'

export const StepsInfo = () => {
    const record = useShowRecordStore((state) => state.record)
    const steps = get(record, 'steps', [])
    const loading = useShowRecordStore((state) => state.loading)

    const items = [
        {
            key: '1',
            label: 'Steps',
            children: (
                size(steps) ?
                    <Steps direction={ 'vertical' } size={ 'small' }>
                        {map(steps, (step, index) => (
                            <Steps.Step
                                key={ `step-${index}` }
                                status={ 'wait' }
                                style={ { overflow: 'auto' } }
                                title={ <Typography.Text>{step}</Typography.Text> }
                                wrapperStyle={ { height: '100%' } }
                            />
                        ))}
                    </Steps> : <ErrorCard/>
            )
        }
    ]

    if (loading) return <Skeleton/>

    if (!record) return null

    return (
        <Flex style={ { height: 'inherit', width: '100%' } } vertical>
            <Tabs
                className={ styles.tabs }
                defaultActiveKey={ '0' }
                items={ items }
                style={ { width: '100%', height: 'inherit' } }
            />
        </Flex>
    )
}
