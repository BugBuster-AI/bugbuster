import { TextWithTooltip } from '@Components/TextWithTooltip';
import { Button, Checkbox, DatePicker, Divider, Form, Input, Modal, Select, Typography } from 'antd';
import { ReactElement, useState } from 'react';
import { useTranslation } from 'react-i18next';

interface IRunForm {
    name: string;
    description: string;
    environment: string;
    host: string;
    deadline: Date;
    checkbox: boolean;
}


// не используется, но оставлено на всякий случай
export const StartNewRun = (): ReactElement => {
    const { t } = useTranslation();
    const [open, setOpen] = useState(false);

    const onFinish = (values: IRunForm) => {
        console.log('Form values:', values);
    };

    return (
        <>
            <Button
                color="primary"
                onClick={ setOpen.bind(null, true) }
                variant="solid"
            >
                {t('run.button_create')}
            </Button>
            <Modal
                cancelText={ t('create_run.buttons.cancel') }
                okText={ t('create_run.buttons.ok') }
                onCancel={ setOpen.bind(null, false) }
                open={ open }
                title={ t('create_run.modal.title') }
            >
                <Form
                    className="middle-form-margin"
                    id="runForm"
                    layout="vertical"
                    onFinish={ onFinish }
                >
                    <Form.Item
                        label="Name"
                        name="name"
                        rules={ [{ required: true, message: 'Please input the name!' }] }
                    >
                        <Input/>
                    </Form.Item>
                    <Form.Item
                        label="Description"
                        name="description"
                        rules={ [{ required: true, message: 'Please input the description!' }] }
                    >
                        <Input.TextArea/>
                    </Form.Item>
                    <Form.Item
                        label="Environment"
                        name="environment"
                        rules={ [{ required: true, message: 'Please select the environment!' }] }
                    >
                        <Select>
                            <Select.Option value="dev">Development</Select.Option>
                            <Select.Option value="staging">Staging</Select.Option>
                            <Select.Option value="prod">Production</Select.Option>
                        </Select>
                    </Form.Item>
                    <Form.Item
                        label="Host"
                        name="host"
                        rules={ [{ required: true, message: 'Please input the host!' }] }
                    >
                        <Input/>
                    </Form.Item>
                    <Form.Item
                        label="Deadline"
                        name="deadline"
                        rules={ [{ required: true, message: 'Please select the deadline!' }] }
                    >
                        <DatePicker/>
                    </Form.Item>
                    <Form.Item
                        name="checkbox"
                        valuePropName="checked"
                    >
                        <Checkbox>
                            <TextWithTooltip
                                text={ 'Test Suite Parallel Execution' }
                                tooltipTitle={ 'title' }
                            />
                        </Checkbox>
                    </Form.Item>

                    <Divider orientation="left" orientationMargin={ 0 } plain>
                        <Typography.Title level={ 5 }>Tests</Typography.Title>
                    </Divider>
                </Form>
            </Modal>
        </>
    );
};
