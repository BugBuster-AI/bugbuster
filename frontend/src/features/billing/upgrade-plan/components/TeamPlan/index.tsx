import { useThemeToken } from '@Common/hooks';
import { Flex, Typography } from 'antd';
import dayjs from 'dayjs';
import map from 'lodash/map';
import upperFirst from 'lodash/upperFirst';
import { CSSProperties, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

export interface ITeamPlanItem {
    itemKey: string
    title: string;
    cost: string;
    untilDate: string;
}

interface IProps {
    activeKey: string;
    onChange?: (value: string) => void
    items: ITeamPlanItem[]
}

export const TeamPlan = ({ items, activeKey, onChange }: IProps) => {
    const [active, setActive] = useState(activeKey)
    const { t } = useTranslation()
    const token = useThemeToken()

    const activeStyles = {
        background: token.colorBgBase,
        boxShadow: `0px 0px 0px 2px rgba(24, 144, 255, 0.2)`,
        border: `1px solid ${token.colorPrimary}`
    } as CSSProperties

    const inactiveStyles = {
        background: token.colorFillTertiary,
        border: `1px solid transparent`,
        cursor: 'pointer'
    } as CSSProperties

    useEffect(() => {
        setActive(activeKey)
    }, [activeKey]);

    useEffect(() => {
        if (onChange) {
            onChange(active)
        }
    }, [active]);

    return (
        <Flex gap={ 8 } style={ { width: '100%' } }>
            {map(items, (item) => {
                const styles = item.itemKey === active ? activeStyles : inactiveStyles

                return <Flex
                    key={ item.itemKey }
                    gap={ 8 }
                    onClick={ setActive.bind(null, item.itemKey) }
                    style={ { borderRadius: 8, width: '100%', padding: 16, ...styles } }
                    vertical
                >
                    <Typography.Text style={ { fontSize: '14px', fontWeight: 700 } }>{item.title}</Typography.Text>
                    <Flex vertical>
                        <Typography.Title
                            level={ 5 }
                            style={ { margin: 0 } }
                        >
                            {item.cost} / {t('common.month')}
                        </Typography.Title>
                        <Typography style={ { fontWeight: 700, color: token.colorTextDescription } }>
                            {upperFirst(t('common.until'))} {dayjs(item.untilDate).format('DD.MM.YYYY')}
                        </Typography>
                    </Flex>
                </Flex>
            })}
        </Flex>
    )
}
