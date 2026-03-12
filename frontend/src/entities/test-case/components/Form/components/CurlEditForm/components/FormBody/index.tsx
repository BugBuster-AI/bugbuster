import { useCurlEditFormContext } from '@Entities/test-case/components/Form/components/CurlEditForm/context';
import { Tabs, TabsProps } from 'antd';
import { useTranslation } from 'react-i18next';
import { HeadersEdit, ParamsEdit, ValidationEdit, VariablesEdit, BodyEdit } from './components';
import styles from './FormBody.module.scss'

export const FormBody = () => {
    const { setActiveTab, activeTab } = useCurlEditFormContext()
    const { t } = useTranslation()

    const items: TabsProps['items'] = [
        {
            key: '1',
            label: t('apiForm.params.name'),
            children: <ParamsEdit/>,
        },
        {
            key: '2',
            label: t('apiForm.headers.name'),
            children: <HeadersEdit/>,
        },
        {
            key: '3',
            label: t('apiForm.body.name'),
            children: <BodyEdit/>,
        },
        {
            key: '4',
            label: t('apiForm.variables.name'),
            children: <VariablesEdit/>,
        },
        {
            key: '5',
            label: t('apiForm.validation.name'),
            children: <ValidationEdit/>,
        },
    ];


    return (
        <Tabs
            activeKey={ activeTab }
            className={ styles.tabs }
            defaultActiveKey={ activeTab }
            items={ items }
            onChange={ setActiveTab }
        />
    )
}
