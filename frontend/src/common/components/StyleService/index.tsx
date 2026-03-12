import { useThemeToken } from '@Common/hooks';
import { useEffect } from 'react';

export const StyleService = () => {

    const token = useThemeToken()

    useEffect(() => {
        const styleSheet = document.styleSheets[0];

        styleSheet.insertRule(
            `:root {
                --primary-color: ${token.colorPrimary};
                --color-icon: ${token.colorIcon};
                --color-success: ${token.colorSuccess};
                --color-error: ${token.colorError};
                --color-step-icon: white;
                --color-border: ${token.colorBorder};
                --color-tree-selected: #e6f4ff;
                --color-warning: ${token.colorWarning};
            }`
        );
    }, []);

    return null
}
