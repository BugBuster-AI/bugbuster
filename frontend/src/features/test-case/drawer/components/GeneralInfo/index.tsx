import { useTestCaseStore } from '@Entities/test-case/store';
import { StepsCaseGroup } from '@Features/test-case/case-steps-group';
import { Flex, Form, Input } from 'antd';
import { ReactElement } from 'react';
import { useTranslation } from 'react-i18next';

export const GeneralInfo = (): ReactElement => {
    const testCase = useTestCaseStore((state) => state.currentCase)
    const { t } = useTranslation()

    return (
        <Flex gap={ 24 } vertical>
            <Form
                className="form-item-no-margin"
                layout={ 'vertical' }
                style={ { display: 'flex', flexDirection: 'column', gap: '24px' } }
            >
                <Flex align={ 'center' } gap={ 16 }>
                    <Form.Item
                        initialValue={ testCase?.priority }
                        label={ t('testCaseDrawer.priority') }
                        name="priority"
                        style={ { flex: 1 } }
                    >
                        <Input disabled/>
                    </Form.Item>
                    <Form.Item
                        initialValue={ testCase?.status }
                        label={ t('testCaseDrawer.status') }
                        name="status"
                        style={ { flex: 1 } }
                    >
                        <Input disabled/>
                    </Form.Item>
                    <Form.Item
                        initialValue={ testCase?.type }
                        label={ t('testCaseDrawer.type') }
                        name="type"
                        style={ { flex: 1 } }
                    >
                        <Input disabled/>
                    </Form.Item>
                </Flex>

                {testCase?.variables && (
                    <Form.Item
                        initialValue={ testCase?.variables }
                        label={ t('testCaseDrawer.variables') }
                        name={ 'variables' }
                    >
                        <Input disabled/>
                    </Form.Item>
                )
                }

                <Form.Item initialValue={ testCase?.url } label={ 'URL' } name="url">
                    <Input disabled/>
                </Form.Item>
            </Form>

            <StepsCaseGroup testCase={ testCase }/>
        </Flex>
    )
}
