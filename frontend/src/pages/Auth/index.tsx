import Logo from '@Assets/icons/light-logo.svg?react';
import AiLogo from '@Assets/icons/screenmate_logo.svg?react'
import { PATHS } from '@Common/consts';
import { VERSION } from '@Common/consts/env.ts';
import { useThemeToken } from '@Common/hooks';
import { Greeting, IGreetingProps } from '@Entities/auth/components/Greeting';
import { LoginPage, SignupPage } from '@Pages/Auth/entities';
import { ResetPasswordPage } from '@Pages/Auth/entities/ResetPassword';
import { Col, Flex, Layout } from 'antd';
import { ReactElement } from 'react';
import { useTranslation } from 'react-i18next';
import { Navigate, Route, Routes } from 'react-router-dom';

const AuthPage = (): ReactElement => {
    const { t } = useTranslation()
    const token = useThemeToken()

    const DATA = {
        ai: {
            title: t('authPage.ai.title'),
            description: t('authPage.ai.description'),
            logo: <AiLogo/>,
            textColor: token.colorText,
            bg: '/images/screenmate-bg.png',
        } as IGreetingProps,

        ru: {
            title: t('authPage.ru.title'),
            description: t('authPage.ru.description'),
            logo: <Logo/>,
            textColor: token.colorTextLightSolid,
            bg: '/images/auth-bg.webp',
        } as IGreetingProps
    }

    const GREETING_DATA = DATA?.[VERSION as 'ru' | 'ai']

    return (
        <Layout style={ { height: '100vh', width: '100%' } }>
            <Flex align="center" justify="center" style={ { height: '100%', width: '100%' } }>
                <Flex style={ { width: '100%', height: '100%' } }>
                    <Greeting span={ 12 } { ...GREETING_DATA } />
                    <Col
                        span={ 12 }
                        style={ {
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                        } }
                    >
                        <Routes>
                            <Route element={ <LoginPage/> } path={ PATHS.AUTH.LOGIN.INDEX }/>
                            <Route element={ <SignupPage/> } path={ PATHS.AUTH.SIGNUP.INDEX }/>
                            <Route element={ <ResetPasswordPage/> } path={ PATHS.AUTH.RESET_PASS.INDEX }/>
                            {/*<Route element={ <GoogleCallback/> } path={ PATHS.AUTH.GOOGLE.INDEX }/>*/}
                            <Route element={ <Navigate to="login"/> } index/>
                        </Routes>
                    </Col>
                </Flex>
            </Flex>
        </Layout>
    );
};

export default AuthPage
