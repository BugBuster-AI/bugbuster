import { BACKEND_URL } from '@Common/api';
import { message, Spin } from 'antd';
import axios from 'axios';
import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

export const GoogleCallback = () => {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate()

    useEffect(() => {
        const handleGoogleCallback = async () => {
            const code = searchParams.get('code');

            if (!code) {
                message.error('Authentication failed: No code received');
                navigate('/auth')

                return;
            }

            try {
                const url = `${BACKEND_URL}auth/google-callback`

                const response = await axios.get(
                    url,
                    { params: { code } }
                );

                const { access_token, picture } = response.data;

                localStorage.setItem('token', access_token);
                localStorage.setItem('user-picture', picture || '');

                navigate('/');
            } catch {
                message.error('Authentication failed. Please try again.');
                navigate('/auth')
            }
        };

        handleGoogleCallback();
    }, [navigate, searchParams]);

    return (
        <div
            style={ {
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                height: '100vh',
            } }
        >
            <Spin>Processing Google authentication...</Spin>
        </div>
    )

}
