import { useThemeToken } from '@Common/hooks';
import { getErrorMessage } from '@Common/utils/getErrorMessage.ts';
import { Header, LogsList, RunningContent } from '@Pages/RunningCase/components';
import { useRunningData } from '@Pages/RunningCase/hooks';
import { useRunningStore } from '@Pages/RunningCase/store';
import { Button, Layout, Result, Spin } from 'antd';
import Sider from 'antd/es/layout/Sider';
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const RunningCase = () => {
    const token = useThemeToken()
    const clearStore = useRunningStore((state) => state.clearStore)
    const isGlobalLoader = useRunningStore((state) => state.isGlobalLoader)
    const error = useRunningStore((state) => state.error)
    const loading = useRunningStore((state) => state.isLoading)
    const navigate = useNavigate()

    const goBack = () => {
        navigate('/')
    }

    useEffect(() => {

        return () => {
            clearStore()
        }
    }, []);

    const { error: errorInfo } = useRunningData()

    const errorMessage = getErrorMessage({ error: errorInfo, needConvertResponse: true })

    return (
        <Layout style={ { overflow: 'hidden', height: '100vh' } }>
            {!error && <Header/>}
            <Spin spinning={ isGlobalLoader } fullscreen />

            {!error ?
                <Layout>
                    {loading ? <Spin style={ { marginTop: '120px' } }/> : <>
                        <Sider
                            style={ {
                                scrollbarWidth: 'thin',
                                borderRight: `1px solid ${token.colorBorder}`,
                                overflow: 'auto'
                            } }
                            theme={ 'light' }
                            width={ 390 }
                        >
                            <div style={ { width: '100%', flex: 1, padding: '24px 24px' } }>
                                <LogsList/>
                            </div>
                        </Sider>

                        <RunningContent/>
                    </>}

                </Layout>
                : (
                    <Result
                        extra={ <Button onClick={ goBack } type="primary">Back Home</Button> }
                        status="404"
                        title={ errorMessage }
                    />
                )
            }
        </Layout>
    )
}

export default RunningCase
