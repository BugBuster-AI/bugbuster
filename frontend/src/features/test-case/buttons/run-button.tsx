import { DownOutlined, PlayCircleOutlined } from '@ant-design/icons';
import { PATHS } from '@Common/consts';
import { asyncHandler } from '@Common/utils';
import { TestCaseApi } from '@Entities/test-case/api';
import { TExecutionEngine } from '@Entities/test-case/models';
import type { MenuProps } from 'antd';
import { Button, ButtonProps, Dropdown, Tooltip } from 'antd';
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
    /** С сервера (CaseRead / вложенный case в прогоне); без дублирования правил на фронте */
    canRunPlaywrightJs?: boolean
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
    from,
    canRunPlaywrightJs = false,
}, ref): ReactElement => {
    const [loading, setLoading] = useState(false)
    const navigate = useNavigate()
    const { t } = useTranslation()
    const fromLocation = window.location.pathname + window.location.search

    const runWithEngine = async (cid: string, engine: TExecutionEngine) => {
        setLoading(true)
        try {
            await asyncHandler(caseApi.runCase.bind(caseApi, cid, engine), {
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
        } finally {
            setLoading(false)
        }
    }

    const handleRun = async (cid: string | string[], engine: TExecutionEngine = 'vlm') => {
        if (disabled) return
        if (!isArray(cid)) {
            await runWithEngine(cid, engine)
        } else {
            console.error('array')
        }
    }

    useImperativeHandle(ref, () => ({
        handleClick: () => {
            void handleRun(case_id as string, 'vlm')
        }
    }))

    const cid = case_id as string
    const chevronColor =
        props?.type === 'primary' || props?.danger
            ? 'rgba(255, 255, 255, 0.92)'
            : 'currentColor'
    const menuItems: MenuProps['items'] = [
        {
            key: 'vlm',
            label: t('codegen.run_vlm'),
            onClick: () => void runWithEngine(cid, 'vlm'),
        },
        {
            key: 'pw',
            disabled: !canRunPlaywrightJs,
            label: !canRunPlaywrightJs
                ? (
                    <Tooltip title={ t('codegen.tooltip_script_disabled') }>
                        <span>{t('codegen.run_script')}</span>
                    </Tooltip>
                )
                : t('codegen.run_script'),
            onClick: () => {
                if (!canRunPlaywrightJs) return
                void runWithEngine(cid, 'playwright_js')
            },
        },
    ]

    if (!isArray(case_id) && !disabled) {
        return (
            <Dropdown menu={ { items: menuItems } } trigger={ ['click'] }>
                <Button
                    disabled={ disabled }
                    icon={ <PlayCircleOutlined/> }
                    loading={ loading || isLoading }
                    { ...props }
                >
                    {t('repository_page.content.toolbar.runs')}
                    <DownOutlined
                        style={ {
                            color: chevronColor,
                            fontSize: 10,
                            marginLeft: 6,
                        } }
                    />
                </Button>
            </Dropdown>
        )
    }

    return (
        <Button
            disabled={ disabled }
            icon={ <PlayCircleOutlined/> }
            loading={ loading || isLoading }
            onClick={ handleRun.bind(null, case_id, 'vlm') }
            { ...props }
        >
            {t('repository_page.content.toolbar.runs')}
        </Button>
    )
})
