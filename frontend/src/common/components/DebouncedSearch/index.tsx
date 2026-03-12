import { LoadingOutlined, SearchOutlined } from '@ant-design/icons';
import { Input, InputProps, InputRef } from 'antd';
import debounce from 'lodash/debounce';
import React, { useState, useCallback, useEffect, useRef, useImperativeHandle, forwardRef } from 'react';
import { useTranslation } from 'react-i18next';

export interface IDebouncedSearchRef {
    clear: () => void;
}

interface IDebouncedSearchProps {
    onChange?: (value: string) => void;
    delay?: number;
    onInput?: (value: string) => void;
    placeholder?: string;
    defaultValue?: string;
    loading?: boolean;
    width?: string | number;
    props?: InputProps;
}

const DebouncedSearchComponent = ({
    onInput,
    loading,
    onChange,
    placeholder,
    delay = 500,
    width = 230,
    props,
    defaultValue = '',
}: IDebouncedSearchProps, ref: React.Ref<IDebouncedSearchRef>) => {
    const [inputValue, setInputValue] = useState(defaultValue);
    const { t } = useTranslation()
    const inputRef = useRef<InputRef>(null);

    const debouncedOnChange = useCallback(
        debounce((value: string) => {
            onChange?.(value);
        }, delay),
        [onChange, delay]
    );

    useEffect(() => {
        return () => {
            debouncedOnChange.cancel();
        };
    }, [debouncedOnChange]);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const value = e.target.value;

        onInput?.(value);
        setInputValue(value);
        debouncedOnChange(value);
    };

    useEffect(() => {
        if (!loading) {
            inputRef?.current?.focus()
        }
    }, [loading]);

    useImperativeHandle(ref, () => ({
        clear: () => {
            setInputValue('');
            onChange?.('');
            inputRef.current?.focus();
        }
    }));

    return (
        <Input
            ref={ inputRef }
            onChange={ handleChange }
            placeholder={ placeholder || t('common.input_search.placeholder') }
            style={ { width: width } }
            suffix={ loading ? <LoadingOutlined/> : <SearchOutlined/> }
            value={ inputValue }
            allowClear
            { ...props }
        />
    );
};

export const DebouncedSearch = forwardRef(DebouncedSearchComponent) as <T = IDebouncedSearchRef>(
    props: IDebouncedSearchProps & { ref?: React.ForwardedRef<T> }
) => ReturnType<typeof DebouncedSearchComponent>;
