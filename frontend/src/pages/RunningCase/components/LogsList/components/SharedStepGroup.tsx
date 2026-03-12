import { useThemeToken } from '@Common/hooks';
import { Flex, Typography } from 'antd';
import { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

interface ISharedStepGroupProps {
    children: ReactNode;
    stepCount: number;
    groupName?: string
    isSelected?: boolean
}

export const SharedStepGroup = ({ 
    children, 
    stepCount ,
    isSelected = false,
}: ISharedStepGroupProps) => {
    const token = useThemeToken();
    const { t } = useTranslation();

    return (
        <Flex
            gap={ 8 }
            style={ {
                border: `1px solid ${token.colorPrimary}`,
                borderRadius: token.borderRadius,
                padding: 12,
                backgroundColor:  token.colorBgContainer,
                position: 'relative',
            } }
            vertical
        >
          
            <Flex
                align="flex-end"
                gap={ 8 }
                justify="space-between"
                style={ {
                    marginBottom: 4,
                    borderRadius: token.borderRadius,
                    padding: `4px 6px`,
                    backgroundColor: isSelected ? token.colorPrimaryBg : 'transparent',
                } }
            >
                <Typography.Text
                    style={ {
                        fontSize: 12,
                        color:  isSelected ? token.colorPrimary : token.colorTextSecondary,
                        fontWeight: 500,
                    } }
                >
                    Shared Step
                    {/* {groupName} */}
                </Typography.Text>
                <Typography.Text
                    style={ {
                        fontSize: 12,
                        whiteSpace: 'nowrap',
                        color: isSelected ? token.colorPrimary : token.colorTextTertiary,
                    } }
                >
                    {stepCount} {t('steps.steps_count', { count: stepCount })}
                </Typography.Text>
            </Flex>
            { children }
        </Flex>
    );
};
