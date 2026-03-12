import { Signup } from '@Features/auth';
import { Space } from 'antd';
import { ReactElement } from 'react';

export const SignupPage = (): ReactElement => {

    return <Space direction="vertical">
        <Signup />
    </Space>
}
