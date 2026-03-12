import { IError } from '@Common/types';
import { WorkspaceApi } from '@Entities/workspace/api';
import { Result, Spin } from 'antd';
import { AxiosError } from 'axios';
import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

const workspaceApi = WorkspaceApi.getInstance()

const AcceptInvite = () => {
    const [searchParams] = useSearchParams()
    const [error, setError] = useState<string | undefined>(undefined)
    const [loading, setLoading] = useState(false)
    const navigate = useNavigate()

    const acceptInvitation = async (token: string) => {
        try {
            await workspaceApi.acceptInvite(token)

            setError(undefined)
            navigate('/')
        } catch (e) {
            const axiosError = e as AxiosError<IError>
            const error = axiosError?.response?.data.detail || 'Something went wrong...'

            if (error && typeof error === 'string') {
                setError(error)
            } else {
                setError('Something went wrong...')
            }
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        const token = searchParams.get('token')

        if (token) {
            acceptInvitation(token)
        }
    }, [searchParams])

    if (loading) {
        return <Spin fullscreen/>
    }

    if (!!error) {
        return <Result status={ 'error' } title={ error }/>
    }

    return null
}

export default AcceptInvite
