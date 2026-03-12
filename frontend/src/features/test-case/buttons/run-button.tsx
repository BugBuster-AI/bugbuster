import { PlayCircleOutlined } from '@ant-design/icons';
import { PATHS } from '@Common/consts';
import { asyncHandler } from '@Common/utils';
import { TestCaseApi } from '@Entities/test-case/api';
import { Button, ButtonProps } from 'antd';
import isArray from 'lodash/isArray';
import { forwardRef, ReactElement, useImperativeHandle, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

interface IProps {
    case_id: string | string[];
    mode?: string
    disabled?: boolean,
    props?: ButtonProps
    isTargetBlank?: boolean
    onClick?: () => void
    loading?: boolean
    from?: string
}

const caseApi = TestCaseApi.getInstance()

export interface IRunButtonRef {
    handleClick: () => void
}

export const RunButton = forwardRef<IRunButtonRef, IProps>(({
    case_id,
    disabled = false,
    isTargetBlank = true,
    props,
    onClick,
    loading: isLoading,
    from
}, ref): ReactElement => {
    const [loading, setLoading] = useState(false)
    const navigate = useNavigate()
    const { t } = useTranslation()
    const fromLocation = window.location.pathname + window.location.search

    const handleClick = async (case_id: string | string[]) => {
        if (disabled) return
        if (!isArray(case_id)) {
            setLoading(true)
            await asyncHandler(caseApi.runCase.bind(null, case_id), {
                errorMessage: t('common.api_error'),
                successMessage: null,
                onSuccess: (data) => {
                    if (isTargetBlank) {
                        window.open(PATHS.RUNNING.ABSOLUTE(data?.run_id!!), '_blank')
                    } else {
                        navigate(PATHS.RUNNING.ABSOLUTE(data?.run_id), {
                            state: {
                                from: from || fromLocation
                            }
                        })
                    }
                    onClick && onClick()
                }
            })
            setLoading(false)
        } else {
            console.error('array')
        }
    }

    useImperativeHandle(ref, () => ({
        handleClick: handleClick.bind(null, case_id)
    }))

    return (
        <Button
            disabled={ disabled }
            icon={ <PlayCircleOutlined/> }
            loading={ loading || isLoading }
            onClick={ handleClick.bind(null, case_id) }
            { ...props }
        >
            {t('repository_page.content.toolbar.runs')}
        </Button>
    )
})
