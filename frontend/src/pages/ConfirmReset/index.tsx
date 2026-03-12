import { ConfirmResetForm } from '@Features/auth/confirm-reset';
import { Flex, Layout } from 'antd';

const ConfirmReset = () => {
    return <Layout style={ { height: '100vh', width: '100%' } }>
        <Flex align="center" justify="center" style={ { height: '100%', width: '100%' } }>
            <ConfirmResetForm/>
        </Flex>
    </Layout>
}

export default ConfirmReset
