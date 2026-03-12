import { Login } from '@Features/auth';
import { Space } from 'antd';
import { ReactElement } from 'react';

export const LoginPage = (): ReactElement => {

    return <Space direction="vertical">
        <Login />
    </Space>
}
