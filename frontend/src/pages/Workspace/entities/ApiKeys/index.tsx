import { Toolbar } from '@Common/components/Toolbar';
import { BaseFlex } from '@Components/BaseLayout';
import { LayoutTitle } from '@Components/LayoutTitle';
import { CreateToken } from '@Features/tokens/create';
import { TokensList } from '@Features/tokens/list';
import { Flex, Typography } from 'antd';
import { useTranslation } from 'react-i18next';

export const ApiKeysPage = () => {
    const { t } = useTranslation()

    return (
        <Flex style={ { height: '100%' } } vertical>
            <LayoutTitle
                title={
                    <Typography.Title level={ 3 } style={ { margin: 0 } }>
                        {t('workspace.api_keys.title')}
                    </Typography.Title>
                }
            />

            <Toolbar
                renderButtons={ <CreateToken/> }
                search={ null } />
            <BaseFlex flex={ 1 } style={ { paddingBlock: 0 } }>
                <TokensList/>
            </BaseFlex>
        </Flex>
    );
};
