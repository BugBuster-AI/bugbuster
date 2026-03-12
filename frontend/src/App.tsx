import { StyleService } from '@Common/components';
import { useMedia } from '@Common/hooks/useMobile';
import { MobilePlaceholder } from '@Components/MobilePlaceholder';
import { useAuthStore } from '@Entities/auth/store/auth.store';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { App as AntdApp, ConfigProvider } from 'antd';
import locale from 'antd/locale/en_US';
import dayjs from 'dayjs';
import { ReactElement, useEffect } from 'react';
import { BrowserRouter } from 'react-router-dom';
import 'modern-normalize/modern-normalize.css';
import '@Assets/styles/index.scss'
import 'dayjs/locale/en.js';
import '../@types/declaration.d.ts'
import { Head } from './Head';
import OVERRIDES from './overrides.ts'
import AppRoutes from './routes';
import THEME from './theme';
import '@fontsource/inter';

dayjs.locale('en');

const App = (): ReactElement => {
    const isMobile = useMedia()
    const queryClient = new QueryClient({
        defaultOptions: {
            queries: {
                retry: 0,
            }
        },
    })
    const logout = useAuthStore((state) => state.logout)

    useEffect(() => {
        window.addEventListener('unauthorized', logout)

        return () => {
            window.removeEventListener('unauthorized', logout)
        }
    }, []);

    if (isMobile) {
        return (
            <QueryClientProvider client={ queryClient }>
                <MobilePlaceholder/>
            </QueryClientProvider>
        )
    }

    return (
        <BrowserRouter>
            <ConfigProvider locale={ locale } theme={ THEME } { ...OVERRIDES }>
                <Head/>
                <QueryClientProvider client={ queryClient }>
                    <AntdApp>
                        <AppRoutes/>
                        <StyleService/>
                    </AntdApp>
                    <ReactQueryDevtools client={ queryClient }/>
                </QueryClientProvider>
            </ConfigProvider>
        </BrowserRouter>
    );
};

export default App;
