import { useThemeToken } from '@Common/hooks';
import { Flex, Typography } from 'antd';
import { ReactElement, ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

interface IProps {
    withoutTitle?: boolean
    treeSlot?: ReactNode
}

export const SuitesTreeList = ({ withoutTitle = false, treeSlot }: IProps): ReactElement => {
    const { t } = useTranslation()
    const token = useThemeToken()

    return (
        <Flex
            gap={ token.margin }
            style={ { paddingRight: token.margin, height: '100%' } }
            vertical
        >
            {!withoutTitle && (
                <Typography.Title level={ 5 } style={ { margin: 0 } }>
                    {t('repository_page.body.sidebar.title')}
                </Typography.Title>
            )}

            {treeSlot}
        </Flex>
    )
}
