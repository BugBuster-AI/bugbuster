import { ArrowUpOutlined } from '@ant-design/icons';
import { useThemeToken } from '@Common/hooks';
import { ETestCasePriority } from '@Entities/test-case/models';
import { Tooltip } from 'antd';
import { useTranslation } from 'react-i18next';

export const TestPriorityIcon = ({ priority = ETestCasePriority.Medium }: {priority?: ETestCasePriority}) => {
    const { t } = useTranslation()
    const token = useThemeToken()
    let icon

    switch (priority) {
        case ETestCasePriority.High:
            icon = <ArrowUpOutlined style={ { color: token.colorError } }/>

            break
        case ETestCasePriority.Medium:
            icon = <ArrowUpOutlined style={ { color: token.colorWarning } }/>

            break
        default:
            icon = <ArrowUpOutlined />

            break
    }

    const title = `${t('casePriorities.index')} ${ t(`casePriorities.${priority}`) }`

    return (
        <Tooltip title={ title }>
            <div style={ { display: 'flex', justifyContent: 'center' } }>
                {icon}
            </div>
        </Tooltip>
    )
}
