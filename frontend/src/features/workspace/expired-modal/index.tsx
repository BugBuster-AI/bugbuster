import { PATHS } from '@Common/consts';
import { useThemeToken } from '@Common/hooks';
import { billingQueries } from '@Entities/billing/queries';
import { EWorkspaceStatus } from '@Entities/workspace/models';
import { useWorkspace } from '@Features/workspace/use-workspace';
import { useQuery } from '@tanstack/react-query';
import { Flex, Modal, Spin, Tag, Typography } from 'antd';
import dayjs from 'dayjs';
import parse from 'html-react-parser';
import map from 'lodash/map';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation, useNavigate } from 'react-router-dom';

export const ExpiredModal = () => {
    const [opened, setOpened] = useState(false)
    const { t } = useTranslation()
    const token = useThemeToken()
    const location = useLocation()
    const { data: workspaceData, isLoading: workspaceLoading } = useWorkspace()
    const workspaceId = workspaceData?.workspace_id

    const { data, isLoading: billingLoading } = useQuery(billingQueries.tariffLimits())

    const isLoading = workspaceLoading || billingLoading

    const handleClose = () => {
        setOpened(false)
    };

    const needOpen = () => {
        if (location.pathname === PATHS.WORKSPACE.BILLING.ABSOLUTE) {
            return false
        }

        return !(!workspaceData || workspaceData?.workspace_status === EWorkspaceStatus.ACTIVE);
    }

    const isNeedOpen = needOpen()

    const navigate = useNavigate()

    const goToBilling = () => {
        if (!workspaceId || !data) return
        const isFree = data?.tariff.is_free

        const basePath = PATHS.WORKSPACE.BILLING.ABSOLUTE

        if (isFree) {
            navigate(basePath)

            handleClose()

            return
        }

        navigate(basePath + `?expiredId=${data.tariff.tariff_id}`);

        handleClose()
    }

    useEffect(() => {
        if (isNeedOpen) {
            setOpened(true)
        }
    }, [isNeedOpen, location]);


    return (
        <Modal
            cancelText={ t('workspace.billing.expiredModal.cancel') }
            okText={ t('workspace.billing.expiredModal.goToBilling') }
            onCancel={ handleClose }
            onOk={ goToBilling }
            open={ opened }
            title={ t('workspace.billing.expiredModal.title') }
            centered
        >
            <Flex gap={ 16 } style={ { paddingBlock: 16 } } vertical>
                {data?.tariff && (
                    <Typography.Text>
                        {parse(t('workspace.billing.expiredModal.subtitle',
                            { date: dayjs(data?.workspace?.tariff_expiration).format('DD.MM.YYYY') }))}
                    </Typography.Text>
                )}

                <Spin spinning={ isLoading }>
                    <Flex
                        gap={ 8 }
                        style={ {
                            padding: 16,
                            border: `1px solid ${token.colorBorder}`,
                            background: token.colorBgBase,
                            borderRadius: 8
                        } }
                        vertical
                    >
                        <Flex align={ 'center' } gap={ 4 }>
                            <Typography.Title
                                level={ 5 }
                                style={ { margin: 0 } }>
                                {parse(data?.tariff?.tariff_full_name || '')}
                            </Typography.Title>
                            <Tag>
                                {t('workspace.billing.expiredModal.currentPlan')}
                            </Tag>
                        </Flex>
                        <Typography.Text type={ 'secondary' }>{data?.tariff?.description}</Typography.Text>

                        <ul style={ { margin: 0, paddingLeft: 16 } }>
                            {map(data?.features, (feature, index) => (
                                <li key={ `expired-feature-${index}` }>{feature}</li>
                            ))}
                        </ul>
                    </Flex>
                </Spin>
            </Flex>
        </Modal>
    )

}
