import { CheckOutlined, CloseOutlined, DashOutlined, LoadingOutlined } from '@ant-design/icons';
import { useThemeToken } from '@Common/hooks';
import { getStepIcon } from '@Common/utils/test-case/step-icon.tsx';
import { EStepType } from '@Entities/test-case/components/Form/models.ts';
import { Badge, Flex, Spin, Tooltip } from 'antd';
import { CSSProperties, ReactNode } from 'react';

enum EStatusIndicator {
    SUCCESS = 'success',
    IDLE = 'idle',
    ERROR = 'error',
    LOADING = 'loading',
    WARNING = 'warning'
}

interface IProps {
    status?: EStatusIndicator
    count?: number | string
    size?: number
    loading?: boolean
    hasResult?: boolean
    icon?: ReactNode
    tooltipTitle?: string
    badgeStyle?: CSSProperties
    className?: string
    elementStyle?: CSSProperties
    baseStyles?: CSSProperties,
    type?: EStepType,
    isSharedStep?: boolean
}


const StatusIndicator = ({
    type = EStepType.STEP,
    status,
    count,
    baseStyles,
    tooltipTitle,
    hasResult,
    size = 24,
    loading,
    className,
    badgeStyle,
    elementStyle,
    isSharedStep
}: IProps) => {
    const token = useThemeToken()

    const getStyles = () => {
        switch (status) {
            case EStatusIndicator.ERROR:
                return {
                    content: <CloseOutlined style={ { width: size / 2, color: token.colorTextLightSolid } }/>,
                    backgroundColor: token.colorError
                }

            case EStatusIndicator.SUCCESS:
                return {
                    backgroundColor: token.colorSuccess,
                    content: <CheckOutlined style={ { width: size / 2, color: token.colorTextLightSolid } }/>
                }
            case EStatusIndicator.WARNING:
                return {
                    backgroundColor: token.colorWarning,
                    content: <CloseOutlined style={ { width: size / 2, color: token.colorTextLightSolid } }/>
                }
            case EStatusIndicator.LOADING:
                return {
                    backgroundColor: 'rgba(240, 240, 240, 1)',
                    content: <Spin
                        indicator={
                            <LoadingOutlined
                                style={ { color: token.colorPrimary, fontSize: size / 1.5 } }
                                spin
                            />
                        }
                    />
                }
            default:
                return {
                    content: count
                        ? <div style={ { fontSize: '12px', color: 'rgba(0,0,0,0.65)' } }>{count}</div> :
                        <DashOutlined/>,
                    backgroundColor: 'rgba(240, 240, 240, 1)'
                }
        }
    }

    let icon: undefined | ReactNode = getStepIcon({
        stepType: type,
        isSharedStep,
        isExpected: hasResult,
        variant: 'circle',
    })

    /*
     * if (isSharedStep) {
     *     icon = <Flex
     *         align={ 'center' }
     *         justify={ 'center' }
     *         style={ {
     *             backgroundColor: 'black',
     *             padding: 3,
     *             width: 15.5,
     *             display: 'flex!important',
     *             height: 16,
     *             border: `1px solid white`,
     *             borderRadius: '50%'
     *         } }>
     *         <Icon component={ () => <SharedStepIcon style={ { color: 'white', width: '11px', height: '11px' } }/> }/>
     *     </Flex>
     * } else if (hasResult) {
     *     icon = ResultIcon
     * } else {
     *     switch (type) {
     *         case EStepType.STEP:
     *             icon = undefined
     *             break
     *         case EStepType.RESULT:
     *             icon = ResultIcon
     *             break
     *         case EStepType.SHARED_STEP:
     *             icon = <Flex
     *                 align={ 'center' }
     *                 justify={ 'center' }
     *                 style={ {
     *                     backgroundColor: 'black',
     *                     padding: 3,
     *                     width: 15.5,
     *                     display: 'flex!important',
     *                     height: 16,
     *                     border: `1px solid white`,
     *                     borderRadius: '50%'
     *                 } }>
     *                 <SharedStepIcon style={ { color: 'white', width: 8, height: 8 } }/>
     *             </Flex>
     *             break
     *         case EStepType.API:
     *             icon = (
     *                 <Flex
     *                     align={ 'center' }
     *                     justify={ 'center' }
     *                     style={ {
     *                         backgroundColor: 'black',
     *                         padding: 3,
     *                         width: 15.5,
     *                         display: 'flex!important',
     *                         height: 16,
     *                         border: `1px solid white`,
     *                         borderRadius: '50%'
     *                     } }>
     *                     <SettingOutlined style={ { minWidth: 8, minHeight: 8, fontSize: 8, color: 'white' } }/>
     *                 </Flex>
     *             )
     *             break
     *     }
     * }
     */

    const { backgroundColor, content } = getStyles()

    return (
        <Tooltip style={ baseStyles } title={ tooltipTitle || undefined }>
            <Badge
                count={ icon }
                rootClassName={ className }
                size={ 'small' }
                style={ { top: '3.5px', insetInlineEnd: '3px', ...badgeStyle } }
            >
                <Flex
                    align={ 'center' }
                    justify={ 'center' }
                    style={ {
                        cursor: 'default',
                        backgroundColor,
                        borderRadius: '50%',
                        minHeight: size,
                        minWidth: size,
                        height: size,
                        width: size,
                        ...elementStyle
                    } }
                >
                    {loading ?
                        <Spin
                            indicator={
                                <LoadingOutlined
                                    style={ { color: token.colorPrimary, fontSize: size / 1.5 } }
                                    spin
                                />
                            }
                        />
                        : content
                    }
                </Flex>
            </Badge>
        </Tooltip>
    )
}

export { StatusIndicator, EStatusIndicator }
