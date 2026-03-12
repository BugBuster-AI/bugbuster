import { EStatusIndicator, StatusIndicator } from '@Common/components';
import { useThemeToken } from '@Common/hooks';
import { Flex, Typography } from 'antd';


interface IProps {
    status?: EStatusIndicator
    title?: string;
    subtitle?: string
    checkStatusInTitle?: boolean
}

const checkSuccessStatus = (value: string) => {
    const regex = new RegExp('success', 'g');

    return regex.test(value) ? EStatusIndicator.SUCCESS : EStatusIndicator.ERROR;
}


export const StatusLabel = ({
    title,
    status: initialStatus = EStatusIndicator.SUCCESS,
    subtitle,
    checkStatusInTitle
}: IProps) => {
    const token = useThemeToken()

    let status = initialStatus

    if (checkStatusInTitle) {
        status = checkSuccessStatus(title || '')
    }

    const getColor = (status?: EStatusIndicator) => {

        if (status === EStatusIndicator.ERROR) {

            return {
                border: token.colorErrorBorder,
                background: token.colorErrorBg
            }
        }


        return {
            border: token.colorSuccessBorder,
            background: token.colorSuccessBg
        }

        /*
         *
         * return {
         *     border: token.colorBorder,
         *     background: token.colorBgBase
         * }
         */
    }

    const colors = getColor(status)

    return (
        <Flex gap={ 8 } style={ { width: '100%' } } vertical>
            <Flex
                align={ 'flex-start' }
                gap={ 16 }
                style={ {
                    width: '100%',
                    border: `1px solid ${colors.border}`,
                    borderRadius: '6px',
                    padding: '20px 24px',
                    backgroundColor: colors.background
                } }
            >
                <StatusIndicator status={ status }/>
                <Flex gap={ 4 } vertical>
                    {Boolean(title) && <Typography.Text>{title}</Typography.Text>}
                    {Boolean(subtitle) && <Typography.Text>{subtitle}</Typography.Text>}
                </Flex>
            </Flex>

        </Flex>
    )
}
