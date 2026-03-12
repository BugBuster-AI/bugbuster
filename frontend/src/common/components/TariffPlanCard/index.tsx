import { useThemeToken } from '@Common/hooks';
import { Flex, Typography } from 'antd';
import map from 'lodash/map';
import { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

interface IProps {
    isBest?: boolean;
    title?: string;
    subtitle?: string;
    cost?: string
    Button?: ReactNode
    features?: string[]
}

export const TariffPlanCard = ({ features, cost, isBest, subtitle, title, Button }: IProps) => {
    const token = useThemeToken()
    const { t } = useTranslation()

    return (
        <Flex
            style={ {
                height: 'auto',
                paddingTop: !isBest ? 32 : '',
                width: 320,
                minWidth: 320,
                background: isBest ? token.controlItemBgActive : '',
                borderRadius: 8
            } }
            vertical>
            {isBest && (
                <Flex align={ 'center' } justify={ 'center' } style={ { padding: '5px 16px' } }>
                    <Typography.Text>{t('plans.best')}</Typography.Text>
                </Flex>
            )}
            <Flex
                gap={ 16 }
                style={ {
                    height: '100%',
                    background: token.colorBgBase,
                    padding: 16,
                    borderRadius: '8px',
                    border: `1px solid ${token.colorBorder}`
                } }
                vertical
            >
                <Flex gap={ 8 } style={ { minHeight: 100 } } vertical>
                    <Flex flex={ '1 0 auto' } vertical>
                        <Typography.Title level={ 5 } style={ { margin: 0 } }>
                            {title}
                        </Typography.Title>
                        <Typography.Text type={ 'secondary' }>
                            {subtitle}
                        </Typography.Text>
                    </Flex>
                    {!!cost && <Typography.Title level={ 5 } style={ { margin: 0 } }>{cost}</Typography.Title>}

                </Flex>
                {Button}

                <ul style={ { display: 'flex', flexDirection: 'column', paddingLeft: 16, margin: 0 } }>
                    {map(features, (item) => {
                        return <li>{item}</li>
                    })}
                </ul>
            </Flex>
        </Flex>
    )
}
