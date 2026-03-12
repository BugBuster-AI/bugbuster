import { QuestionCircleOutlined } from '@ant-design/icons';
import { useThemeToken } from '@Common/hooks';
import { Tooltip, TooltipProps, Typography } from 'antd';
import { TextProps } from 'antd/es/typography/Text';
import { ReactElement, ReactNode } from 'react';

interface IProps {
    text: string | ReactNode;
    tooltipTitle?: string | ReactNode
    textProps?: TextProps
    tooltipProps?: TooltipProps
}

export const TextWithTooltip = ({ tooltipTitle, text, textProps, tooltipProps }: IProps): ReactElement => {
    const token = useThemeToken()

    return <Typography.Text style={ { display: 'flex', gap: '4px', alignItems: 'center' } } { ...textProps }>
        {text}
        {!!tooltipTitle && (
            <Tooltip title={ tooltipTitle } { ...tooltipProps }>
                <QuestionCircleOutlined style={ { color: token.colorIcon } }/>
            </Tooltip>
        )
        }
    </Typography.Text>
}
