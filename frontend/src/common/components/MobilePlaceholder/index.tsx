import { LoadingOutlined } from '@ant-design/icons';
import MailChecked from '@Assets/icons/mobile/mail-checked.svg?react'
import PersonPc from '@Assets/icons/mobile/pc-person.svg?react'
import BBLogo from '@Assets/icons/regular_bb_logo.svg?react'
import ScreenmateLogo from '@Assets/icons/screenmate_logo.svg?react'
import { VERSION } from '@Common/consts/env';
import { useFastSignup } from '@Entities/auth/queries/mutations.ts';
import { Flex, Form, Input, Spin } from 'antd';
import { useForm } from 'antd/es/form/Form';
import { AxiosError } from 'axios';
import cn from 'classnames'
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import styles from './MobilePlaceholder.module.scss'

interface IForm {
    email: string
}

const getLogo = () => {

    if (VERSION === 'ru') {
        return <BBLogo height={ 24 }/>
    }

    return <ScreenmateLogo height={ 24 }/>
}

const getErrorMsg = (status: number, t: (v: string) => string) => {
    switch (status) {
        case 400:
            return t(`mobilePlaceholder.${VERSION}.first.errors.alreadyUser`)
        default:
            return t(`mobilePlaceholder.${VERSION}.first.errors.default`)
    }
}

export const MobilePlaceholder = () => {
    const { t } = useTranslation()
    const [isChecked, setIsChecked] = useState(false)
    const [value, setValue] = useState('')
    const [form] = useForm<IForm>()

    const { mutate, isSuccess, error, isPending } = useFastSignup()

    useEffect(() => {
        const checked = sessionStorage.getItem('emailChecked')

        if (checked) {
            setIsChecked(true)
        } else {
            setIsChecked(false)
        }
    }, []);

    const handleSubmit = () => {
        if (!value) {
            return
        }
        mutate(value)
    }

    useEffect(() => {
        if (isSuccess) {
            setIsChecked(true)
            sessionStorage.setItem('emailChecked', 'value')
            setValue('')

            return
        }

        if (error) {
            const axiosError = error as AxiosError
            const msg = getErrorMsg(axiosError?.status || 500, t)

            setIsChecked(false)
            setValue('')

            form.setFields([
                {
                    name: 'email',
                    errors: [msg]
                }
            ])
        }
    }, [isSuccess, error]);


    const content = () => {
        if (isChecked) {
            return <>
                <MailChecked/>
                <h6>{t(`mobilePlaceholder.${VERSION}.checked.title`)}</h6>
                <p>{t(`mobilePlaceholder.${VERSION}.checked.description`)}</p>
            </>
        }

        return <Form
            className={ styles.formItem }
            form={ form }
            onFinish={ handleSubmit }
        >

            <PersonPc/>
            <h6>{t(`mobilePlaceholder.${VERSION}.first.title`)}</h6>
            <p>{t(`mobilePlaceholder.${VERSION}.first.description`)}</p>

            <div>
                <Form.Item
                    name={ 'email' }
                    rules={ [
                        {
                            required: true,
                            message: t(`mobilePlaceholder.${VERSION}.first.error`)
                        },
                        {
                            type: 'email',
                            message: t(`mobilePlaceholder.${VERSION}.first.emailError`)
                        }
                    ] }
                >
                    <Input
                        onChange={ (e) => setValue(e.target.value) }
                        placeholder={ t(`mobilePlaceholder.${VERSION}.first.input`) }
                        size={ 'large' }
                        value={ value }
                    />
                </Form.Item>

            </div>
            <Spin indicator={ <LoadingOutlined/> } spinning={ isPending }>
                <button type={ 'submit' }>{t(`mobilePlaceholder.${VERSION}.first.button`)}</button>
            </Spin>
        </Form>
    }

    return (
        <Flex
            align={ 'center' }
            className={ styles.wrapper }
            flex={ 1 }
            justify={ 'center' }
            vertical
        >
            {getLogo()}
            <Flex align={ 'center' } className={ cn(styles.form, { [styles.checked]: isChecked }) } vertical>
                {content()}
            </Flex>
        </Flex>
    )
}
