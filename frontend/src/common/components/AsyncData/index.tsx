import { ApiError } from '@Common/types';
import { getErrorMessage } from '@Common/utils/getErrorMessage.ts';
import { QueryKey, UseQueryOptions, useQuery } from '@tanstack/react-query';
import { Result, Spin } from 'antd';
import get from 'lodash/get';
import { Children, cloneElement, ReactElement, useEffect } from 'react';

interface IChildrenData<TData> {
    error?: string;
    loading?: boolean;
    data?: TData;
}

interface IProps<TQueryFnData, TError = Error, TData = TQueryFnData, TQueryKey extends QueryKey = QueryKey> {
    queryOptions: UseQueryOptions<TQueryFnData, TError, TData, TQueryKey>;
    children: ReactElement<IChildrenData<TData>>;
    showError?: boolean;
    dataKey?: string;
    onDataLoad?: (data: TData) => void;
    transformData?: (data: TData) => unknown;
    onError?: (error: TError) => void;
    onLoading?: (loading: boolean) => void
}

export const AsyncData = <
    TQueryFnData,
    TError = Error,
    TData = TQueryFnData,
    TQueryKey extends QueryKey = QueryKey
>({
        children,
        queryOptions,
        onError,
        transformData,
        onDataLoad,
        onLoading,
        dataKey,
        showError = true
    }: IProps<TQueryFnData, TError, TData, TQueryKey>) => {
    const { data, isLoading, error } = useQuery<TQueryFnData, TError, TData, TQueryKey>(queryOptions);

    const errorMessage = getErrorMessage({
        error: (error as any)?.response?.data as ApiError
    });

    useEffect(() => {
        if (onLoading) {
            onLoading(isLoading);
        }
    }, [isLoading]);

    useEffect(() => {
        if (data) {
            onDataLoad?.(data);
        }
    }, [data, onDataLoad]);

    useEffect(() => {
        if (error) {
            onError?.(error);
        }
    }, [error, onError]);

    if (showError && !!errorMessage) {
        return <Result status={ 'error' } style={ { flex: 1 } } title={ errorMessage }/>;
    }

    const currentData = dataKey ? get(data, dataKey, []) : data;
    const transformedData = transformData ? transformData(currentData as TData) : currentData;

    return (
        <Spin spinning={ isLoading }>
            {Children?.map(children, (child) =>
                cloneElement(child, {
                    data: transformedData as TData,
                    loading: isLoading,
                    error: errorMessage
                })
            )}
        </Spin>
    );
};
