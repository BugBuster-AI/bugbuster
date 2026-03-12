import { DebouncedSearch, IDebouncedSearchRef } from '@Components/DebouncedSearch';
import { QueryOptions, useQuery, keepPreviousData } from '@tanstack/react-query';
import { Flex, Select, SelectProps } from 'antd';
import map from 'lodash/map';
import { useEffect, useRef, useState } from 'react';

interface IProps<T> extends SelectProps {
    queryOptions: QueryOptions<T[], any, any, any>
    keyIndex?: keyof T
    labelIndex?: keyof T
    disabled?: boolean
    labelTransform?: (label: string) => string
    defaultValue?: ((data?: T) => string) | null
    onLoadData?: (data: T) => void
    enableSearch?: boolean
    onSearchChange?: (value: string) => void
}

export const AsyncSelect =
    <T, >({
        queryOptions,
        labelTransform,
        keyIndex,
        labelIndex,
        disabled,
        defaultValue,
        onLoadData,
        enableSearch = false,
        onSearchChange,
        ...props
    }: IProps<T>) => {
        const [open, setOpen] = useState(false)
        const searchRef = useRef<IDebouncedSearchRef>(null)

        // @ts-ignore
        const { data, isLoading, isFetching } = useQuery({
            ...queryOptions,
            ...(enableSearch && { placeholderData: keepPreviousData })
        })
        
        const defaultDataValue = keyIndex ? data?.[0]?.[keyIndex] : data?.[0]
        const defaultCustomValue = defaultValue ? defaultValue(data) : undefined

        useEffect(() => {
            if (onLoadData && data) {
                onLoadData(data)
            }
        }, [data, onLoadData]);

        const handleResetSearch = () => {
            searchRef?.current?.clear()
        }

        useEffect(() => {
            if (!open) {
                handleResetSearch()
            }
        }, [open]);

        const handleSearchChange = (value: string) => {
            onSearchChange?.(value)
        }

        if (!data) return null

        const renderOptions = () => map((data || []), (item: T) => {
            const label = (labelIndex ? ((item)?.[labelIndex] || '') : item) as string
            const key = (keyIndex ? ((item)?.[keyIndex] || '') : item) as string
            const resultLabel = labelTransform ? labelTransform(label) : label

            return (
                <Select.Option key={ key }>
                    {resultLabel}
                </Select.Option>
            )
        })

        if (!enableSearch) {
            return (
                <Select
                    defaultValue={ defaultValue === null ? undefined : defaultCustomValue || defaultDataValue }
                    disabled={ disabled }
                    loading={ isLoading }
                    { ...props }
                >
                    {renderOptions()}
                </Select>
            )
        }

        return (
            <Select
                defaultValue={ defaultValue === null ? undefined : defaultCustomValue || defaultDataValue }
                disabled={ disabled }
                dropdownRender={ (menu) => (
                    <Flex gap={ 4 } vertical>
                        <DebouncedSearch
                            ref={ searchRef }
                            loading={ isFetching }
                            onChange={ handleSearchChange }
                            width={ 'auto' }
                        />
                        {menu}
                    </Flex>
                ) }
                loading={ isLoading || isFetching }
                onDropdownVisibleChange={ setOpen }
                { ...props }
            >
                {renderOptions()}
            </Select>
        )
    }
