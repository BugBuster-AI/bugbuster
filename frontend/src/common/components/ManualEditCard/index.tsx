import { CheckOutlined, UploadOutlined } from '@ant-design/icons';
import { StatusBadge } from '@Common/components/StatusBadge';
import { CLASSNAMES } from '@Common/consts/css.ts';
import { Uploader } from '@Components/Uploader';
import { ERunStatus } from '@Entities/runs/models';
import { EStepType } from '@Entities/test-case/components/Form/models.ts';
import {
    IManualStepValue
} from '@Pages/Runs/entities/Details/components/Drawer/components/Execution/components/ManualEdit';
import { Button, Flex, Input, Spin, Typography } from 'antd';
import cn from 'classnames';
import parse from 'html-react-parser';
import isString from 'lodash/isString';
import map from 'lodash/map';
import { CSSProperties, ReactNode, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

type TStatus = ERunStatus

export interface IEditCardInfo {
    comment?: string
    files?: File[]
    prevStatus?: ERunStatus
}

interface IProps {
    label: string | ReactNode;
    initialValue?: IManualStepValue
    stepType?: EStepType
    onChange?: (
        status?: ERunStatus,
        info?: IEditCardInfo
    ) => void
    style?: CSSProperties
    value?: ERunStatus
    resettable?: boolean
    onFailed?: (info: IEditCardInfo) => void
    formVisible?: boolean
    disabled?: boolean
    onDropFile?: (files?: File[]) => void
    formDisabled?: boolean
    enableCopyButton?: boolean
    pending?: boolean
    rawLabel: string
}

export const ManualEditCard =
    ({
        label,
        value,
        onFailed,
        onChange,
        onDropFile,
        disabled,
        style,
        stepType,
        formVisible,
        initialValue,
        resettable = true,
        formDisabled,
        pending = false,
        rawLabel,
        enableCopyButton

    }: IProps) => {
        const [isCopied, setIsCopied] = useState(false)
        const { t } = useTranslation()
        const [initialFormData, setInitialFormData] = useState<IManualStepValue | undefined>(initialValue)
        const [currentStatus, setCurrentStatus] = useState<TStatus | undefined>(initialValue?.status || undefined)
        const [comment, setComment] = useState<string | undefined>(undefined)
        const [files, setFiles] = useState<File[] | undefined>(undefined)
        const [loading, setLoading] = useState(false)

        const handleClick = (status: TStatus) => {
            if (disabled && status === ERunStatus.PASSED) return
            if (status === currentStatus) {
                if (resettable) {
                    onChange && onChange(undefined, { prevStatus: currentStatus })
                    setCurrentStatus(undefined)
                }

                return
            }
            onChange && onChange(status, { prevStatus: currentStatus, comment, files })
        }


        useEffect(() => {
            setCurrentStatus(value)
        }, [value]);

        const loadFiles = async () => {
            setLoading(true)
            const files = await Promise.all(
                map(initialValue?.attachments, async (file) => {
                    const response = await fetch(file.url);
                    const blob = await response.blob();

                    return new File([blob], file.file, { type: blob.type });
                }) || []
            );

            setLoading(false)
            setFiles(files)
        }

        useEffect(() => {
            setInitialFormData(initialValue)
            setComment((prev) => (!prev ? initialValue?.comment : prev))

            if (!files) {
                loadFiles()
            }
        }, [initialValue]);

        const disabledStyles = disabled ? {
            opacity: 0.5,
            cursor: 'not-allowed'
        } : {}

        const handleCopy = async () => {
            if (isCopied || !value) {
                return
            }

            await navigator.clipboard.writeText(rawLabel)

            setIsCopied(true)
        }

        useEffect(() => {
            let timeout

            if (isCopied) {
                timeout = setTimeout(() => {
                    setIsCopied(false)
                }, 2000)
            }

            return () => {
                clearInterval(timeout)
            }
        }, [isCopied]);

        return (
            <Spin spinning={ pending }>

                <Flex gap={ 8 } style={ { paddingBottom: '16px', ...style } } vertical>

                    <Typography.Text
                        className={ cn(CLASSNAMES.testCaseStepName, CLASSNAMES.stepType(stepType)) }
                    >
                        {isString(label) ? parse(label) : label}
                    </Typography.Text>

                    <Flex gap={ 16 } vertical>
                        <Flex gap={ 8 }>
                            <StatusBadge
                                label={ t('statuses.passed') }
                                onClick={ handleClick.bind(null, ERunStatus.PASSED) }
                                status={ currentStatus === ERunStatus.PASSED ? ERunStatus.PASSED : undefined }
                                style={ { cursor: 'pointer', ...disabledStyles } }
                            />
                            <StatusBadge
                                label={ t('statuses.failed') }
                                onClick={ onFailed?.bind(null, { comment, files }) }
                                status={ currentStatus === ERunStatus.FAILED ? ERunStatus.FAILED : undefined }
                                style={ { cursor: 'pointer' } }
                            />

                            {enableCopyButton && (
                                <Button
                                    color={ isCopied ? 'green' : 'primary' }
                                    disabled={ isCopied }
                                    icon={ isCopied && <CheckOutlined/> }
                                    onClick={ handleCopy }
                                    size={ 'small' }
                                    style={ isCopied ? { background: '#52c41a', color: 'white' } : undefined }
                                    type={ 'primary' }
                                    variant={ 'solid' }
                                >
                                    {t(`common.${isCopied ? 'simpleCopied' : 'copy'}`)}
                                </Button>
                            )}
                        </Flex>

                        {formVisible && (
                            <>
                                <Input.TextArea
                                    defaultValue={ initialFormData?.comment }
                                    disabled={ formDisabled }
                                    onChange={ (e) => setComment(e.target.value) }
                                    placeholder={ t('common.description') }
                                    value={ comment }
                                />
                                {disabled}
                                {!loading && <Uploader
                                    defaultFileList={ files }
                                    disabled={ formDisabled }
                                    onDropFile={
                                        (files) => {
                                            setFiles(files)
                                            onDropFile && onDropFile(files)
                                        }
                                    }

                                    type={ 'default' }>
                                    <Button
                                        disabled={ formDisabled }
                                        icon={ <UploadOutlined/> }
                                        style={ { width: 'fit-content' } }
                                    >
                                        {t('common.upload')}
                                    </Button>
                                </Uploader>}
                            </>
                        )}
                    </Flex>
                </Flex>
            </Spin>
        )
    }
