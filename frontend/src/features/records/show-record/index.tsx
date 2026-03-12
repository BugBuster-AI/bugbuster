import { Aside, ShowView, ShowContent } from '@Features/records/show-record/components';
import { useShowRecordData } from '@Features/records/show-record/hooks/useRecordData';
import { Col, Flex } from 'antd';

export const ShowRecord = () => {
    useShowRecordData()

    return (
        <ShowView>
            <Flex style={ { overflow: 'hidden', height: '75vh' } }>
                <Col span={ 12 }>
                    <Aside/>
                </Col>
                <Col span={ 12 }>
                    <ShowContent/>
                </Col>
            </Flex>
        </ShowView>
    )
}
