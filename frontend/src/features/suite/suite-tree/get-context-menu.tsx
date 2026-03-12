import Icon, { CopyOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons';
import AiIcon from '@Assets/icons/ai-icon.svg?react'
import { MenuProps } from 'antd';

export enum EMenuKeys {
    EDIT_SUITE = 'edit_suite',
    CLONE_SUITE = 'clone_suite',
    DELETE_SUITE = 'delete_suite',
    CREATE_SUBSUITE = 'create_subsuite',
    CREATE_CASE = 'create_case',
    GENERATE_CASES = 'generate_cases'
}

export const getContextMenu = (): MenuProps['items'] => {

    return  [
        {
            key: EMenuKeys.EDIT_SUITE,
            label: (
                <div>
                    test
                </div>
            ),
            icon: <EditOutlined />,
        },
        {
            key: EMenuKeys.CLONE_SUITE,
            label: 'Clone suite',
            icon: <CopyOutlined />
        },
        {
            type: 'divider',
        },
        {
            key: EMenuKeys.CREATE_SUBSUITE,
            label: 'Create subsuite',
            icon: <PlusOutlined />
        },
        {
            key: EMenuKeys.CREATE_CASE,
            label: 'Create case',
            icon: <PlusOutlined />
        },
        {
            key: EMenuKeys.GENERATE_CASES,
            label: 'Generate cases',
            icon: <Icon component={ AiIcon } />
        }
    ]
}
