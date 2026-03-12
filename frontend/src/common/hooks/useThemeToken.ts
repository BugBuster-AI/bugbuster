import {GlobalToken as GlobalTokenType} from '@ant-design/cssinjs-utils'
import {IAppToken} from '@Common/types/theme.ts';
import {GlobalToken, theme} from 'antd';
import type {AliasToken} from 'antd/es/theme/interface/alias';
import type {ComponentTokenMap} from 'antd/es/theme/interface/components';

const { useToken } = theme

type AppAliasToken = AliasToken & IAppToken

export type AppGlobalToken = GlobalTokenType<ComponentTokenMap, AppAliasToken>;

export const useThemeToken = (): GlobalToken => {
    const { token } = useToken();

    return token
}
