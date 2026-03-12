import { ConfigProviderProps } from 'antd';

export default {
    form: {
        style: {
            '.ant-row': {
                backgroundColor: 'blue'
            }
        }
    },
    iconPrefixCls: 'custom-icon',
    typography: {
        style: {
            margin: 0
        }
    },

} as Omit<ConfigProviderProps, 'theme'>
