import { AsyncSelect } from '@Common/components';
import { IProjectListItem } from '@Entities/project';
import { projectQueries } from '@Entities/project/queries';
import { IProfileForm } from '@Entities/users/models/profile-form.dto.ts';
import { userQueries } from '@Entities/users/queries';
import { Form, Input, Flex, FormProps } from 'antd';
import { useTranslation } from 'react-i18next';

interface IProps extends FormProps {
    emailDisabled?: boolean
}

export const ProfileForm = ({ emailDisabled, ...props }: IProps) => {
    const { t } = useTranslation();

    return (
        <Form<IProfileForm> layout={ 'vertical' } { ...props }>
            <Form.Item
                label={ t('users.invite_modal.email.label') }
                name="email"
                rules={ [
                    {
                        required: true, message: t('errors.input.required')
                    },
                    {
                        type: 'email',
                        message: t('errors.input.email')
                    }
                ] }
            >
                <Input
                    disabled={ emailDisabled }
                    placeholder={ t('users.invite_modal.email.placeholder') }
                />
            </Form.Item>

            <Flex flex={ 1 } gap={ 16 } style={ { width: '100%' } }>

                <Form.Item
                    label={ t('users.invite_modal.first_name.label') }
                    name="first_name"
                    rules={ [{ required: true, message: t('errors.input.required') }] }
                    style={ { flex: 1 } }

                >
                    <Input placeholder={ t('users.invite_modal.first_name.placeholder') }/>
                </Form.Item>

                <Form.Item
                    label={ t('users.invite_modal.last_name.label') }
                    name="last_name"
                    rules={ [{ required: true, message: t('errors.input.required') }] }
                    style={ { flex: 1 } }
                >
                    <Input placeholder={ t('users.invite_modal.last_name.placeholder') }/>
                </Form.Item>
            </Flex>

            <Form.Item
                label={ t('users.invite_modal.role_title.label') }
                name="role_title"
                rules={ [{ required: true, message: t('errors.input.required') }] }
            >
                <Input placeholder={ t('users.invite_modal.role_title.placeholder') }/>
            </Form.Item>

            <Form.Item
                label={ t('users.invite_modal.role.label') }
                name="role"
                rules={ [{ required: true, message: t('errors.input.required') }] }
            >
                <AsyncSelect
                    defaultValue={ null }
                    placeholder={ t('users.invite_modal.role.placeholder') }
                    queryOptions={ userQueries.roles() }/>
            </Form.Item>

            <Form.Item
                label={ t('users.invite_modal.projects.label') }
                name="project_ids"
                rules={ [{ required: true, message: t('errors.input.required') }] }
            >
                <AsyncSelect<IProjectListItem>
                    defaultValue={ props?.initialValues ? undefined : null }
                    keyIndex={ 'project_id' }
                    labelIndex={ 'name' }
                    mode={ 'multiple' }
                    placeholder={ t('users.invite_modal.projects.placeholder') }
                    queryOptions={ projectQueries.list() }
                />

            </Form.Item>

        </Form>
    );
};

