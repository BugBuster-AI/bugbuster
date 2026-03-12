import { StepsInfo } from '@Features/records/show-record/components/StepsInfo';
import { Flex } from 'antd';

export const Aside = () => {
    return (
        <Flex style={ { width: '100%', overflow: 'hidden', height: '100%' } }>
            <Flex
                gap={ 24 }
                style={ { scrollbarWidth: 'thin', width: '100%', height: '100%', paddingRight: '24px' } }
                vertical
            >
                <StepsInfo/>
            </Flex>
        </Flex>
    )
}
