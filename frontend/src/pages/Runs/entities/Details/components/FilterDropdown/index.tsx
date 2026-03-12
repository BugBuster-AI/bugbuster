import { runsQueries } from '@Entities/runs/queries';
import { useGroupedRunStore } from '@Pages/Runs/entities/Details/store';
import { useQuery } from '@tanstack/react-query';
import {
    Dropdown,
    Checkbox,
    Typography,
    Button,
    Menu,
    Divider,
    Badge,
} from 'antd';
import includes from 'lodash/includes';
import isEqual from 'lodash/isEqual';
import size from 'lodash/size';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router-dom';

const StatusFilter = () => {
    const { t } = useTranslation();
    const [searchParams, setSearchParams] = useSearchParams();
    const updateFilters = useGroupedRunStore((state) => state.updateFilters);
    const clearFilters = useGroupedRunStore((state) => state.clearFilters);
    const filters = useGroupedRunStore((state) => state.filters);
    const [open, setOpen] = useState(false);

    // Обновление URL параметров
    const updateUrlParams = (newFilters: string[]) => {
        const newParams = new URLSearchParams(searchParams);

        if (newFilters.length > 0) {
            newParams.set('status', newFilters.join('|'));
        } else {
            newParams.delete('status');
        }
        if (newParams.toString() !== searchParams.toString()) {
            setSearchParams(newParams);
        }
    };

    const handleCheckboxChange = (value: string) => {
        const newFilters = filters.includes(value)
            ? filters.filter((item) => item !== value)
            : [...filters, value];

        updateFilters(newFilters);
        updateUrlParams(newFilters);
    };

    const handleClear = () => {
        clearFilters();
        searchParams.delete('status');
        setSearchParams(searchParams);
    };

    useEffect(() => {
        const statusParam = searchParams.get('status');
        const urlFilters = statusParam ? statusParam.split('|') : [];

        if (!isEqual(filters.sort(), urlFilters.sort())) {
            updateFilters(urlFilters);
        }
    }, [searchParams]);

    
    useEffect(() => {
        const statusParam = searchParams.get('status');

        if (statusParam) {
            updateFilters(statusParam.split('|'));
        }
    }, []);

    const { data: keys } = useQuery(runsQueries.statusList())

    return (
        <Dropdown
            dropdownRender={ () => {
                return (
                    <Menu style={ { width: 230 } }>
                        <Menu.Item disabled>
                            <Typography.Text>Status</Typography.Text>
                        </Menu.Item>

                        {keys?.map((status, index) => {
                            const isChecked = includes(filters, status);

                            return (
                                <Menu.Item
                                    key={ `statusKey-${status}-${index}` }
                                    onClick={ (e) => {
                                        e.domEvent.stopPropagation()
                                        handleCheckboxChange(status)

                                        throw 'break'
                                    } }
                                >
                                    <Checkbox checked={ isChecked }>
                                        {t(`statuses.${status}`)}
                                    </Checkbox>
                                </Menu.Item>
                            );
                        })}

                        <Divider style={ { marginBlock: '4px' } }/>

                        <Button onClick={ handleClear } type="link">
                            {t('filters.clear')}
                        </Button>
                    </Menu>
                );
            } }

            onOpenChange={ (e) => {
                setOpen(e)
            } }

            open={ open }
            trigger={ ['click'] }
        >
            <Badge count={ size(filters) } dot>
                <Button
                    onClick={ setOpen.bind(null, !open) }
                    style={ { padding: 0, margin: 0, height: 'fit-content' } }
                    type="link"
                >
                    Status Filter
                </Button>
            </Badge>
        </Dropdown>
    );
};

export default StatusFilter;
