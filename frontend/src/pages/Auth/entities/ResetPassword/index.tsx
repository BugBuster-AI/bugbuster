import { ResetPassword } from '@Features/auth/reset-password';
import { Space } from 'antd';
import { ReactElement } from 'react';

export const ResetPasswordPage = (): ReactElement => {

    return <Space direction="vertical">
        <ResetPassword />
    </Space>
}
