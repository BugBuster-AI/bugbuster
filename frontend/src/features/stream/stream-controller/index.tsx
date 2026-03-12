import { getErrorMessage } from '@Common/utils/getErrorMessage.ts';
import { streamQueries } from '@Entities/stream/queries';
import { useStreamStore } from '@Entities/stream/store';
import { useQuery } from '@tanstack/react-query';
import { PropsWithChildren, useEffect, useState } from 'react';

interface IProps extends PropsWithChildren {
    projectId?: string
}

const DEFAULT_INTERVAL = 5000

export const StreamController = ({ children, projectId }: IProps) => {
    const setStreams = useStreamStore((state) => state.setStreams)
    const [refetchInterval, setRefetchInterval] = useState(DEFAULT_INTERVAL)

    const { data, isLoading, error } = useQuery(streamQueries.statList({
        refetchInterval: (query) => {
            if (query.state.error) {
                return false;
            }

            return refetchInterval
        }
    }))

    useEffect(() => {
        const errorMessage = getErrorMessage({ error, needConvertResponse: true })

        setStreams(data, isLoading, errorMessage, projectId || undefined)
    }, [data, isLoading, error, projectId]);

    useEffect(() => {
        return () => {
            setRefetchInterval(0)
        }
    }, []);

    return children
}
