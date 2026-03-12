import { useThemeToken } from '@Common/hooks';
import { getLimits } from '@Common/utils/getLimits';
import { BaseFlex } from '@Components/BaseLayout';
import { LayoutTitle } from '@Components/LayoutTitle';
import { ELimitType } from '@Entities/workspace/models';
import { useWorkspaceStore } from '@Entities/workspace/store';
import { UsersList } from '@Features/users/list';
import { UsersToolbar } from '@Pages/Workspace/entities/Users/components/Toolbar';
import { Flex, Typography } from 'antd';
import find from 'lodash/find';
import { useTranslation } from 'react-i18next';

export const UsersPage = () => {
    const { t } = useTranslation()
    const token = useThemeToken()
    const limits = useWorkspaceStore((state) => state.limits)
    const currentLimit = find(limits, { feature_name: ELimitType.INVITE_USER })

    const { title } = currentLimit ? getLimits({
        remaining: currentLimit.remaining,
        limitValue: currentLimit.limit_value
    }) : {}

    return (
        <Flex vertical>
            <LayoutTitle
                title={ (
                    <Flex align={ 'baseline' } gap={ 16 }>
                        <Typography.Title level={ 3 } style={ { margin: 0, wordBreak: 'keep-all' } }>
                            {t('users.title')}
                        </Typography.Title>
                        <Typography.Text style={ { color: token.colorTextDescription } }>
                            {title}
                        </Typography.Text>
                    </Flex>
                ) }
            />

            <UsersToolbar/>

            <BaseFlex flex={ 1 }>
                <UsersList/>
            </BaseFlex>
        </Flex>
    )
}
