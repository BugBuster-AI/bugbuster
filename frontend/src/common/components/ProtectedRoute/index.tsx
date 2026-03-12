import { PATHS } from '@Common/consts';
import { getToken } from '@Common/utils/token.ts';
import { ELoginStatus, useAuthStore } from '@Entities/auth/store/auth.store.ts';
import { Spin } from 'antd';
import compact from 'lodash/compact';
import isEmpty from 'lodash/isEmpty';
import split from 'lodash/split';
import { ReactNode, useEffect } from 'react';
import { Navigate, Outlet } from 'react-router-dom';

const useAuthRedirect = (hasToken: boolean) => {
    const { logout, getUser } = useAuthStore();

    useEffect(() => {
        if (hasToken) {
            getUser();
        } else {
            logout();
        }
    }, [hasToken]);

};

interface IProps {
    children: ReactNode;
    type?: 'private' | 'public';
}

export const ProtectedRoute = ({
    children,
    type = 'private',
}: IProps): ReactNode => {
    const { loginStatus } = useAuthStore();
    const hasToken = getToken();

    useAuthRedirect(Boolean(hasToken));

    if (loginStatus === ELoginStatus.IDLE || loginStatus === ELoginStatus.LOADING) {
        return <Spin fullscreen/>;
    }

    if (type === 'private' && loginStatus === ELoginStatus.UN_AUTH) {
        const redirect_url = window.location.href
        const redirect_pathname = window.location.pathname

        const isEmptyPath = isEmpty(compact(split(redirect_pathname, '/')))
        const isAuthUrl = redirect_pathname.startsWith(PATHS.AUTH.ABSOLUTE)

        const url = (!isEmptyPath && !isAuthUrl)
            ? `${PATHS.AUTH.LOGIN.ABSOLUTE}?redirect_url=${redirect_url}`
            : PATHS.AUTH.LOGIN.ABSOLUTE

        return <Navigate to={ url }/>;
    }

    if (type === 'public' && loginStatus === ELoginStatus.IS_AUTH) {

        return <Navigate to={ PATHS.INDEX }/>;
    }

    return children ? children : <Outlet/>;
};
