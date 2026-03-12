import { PAGINATION } from '@Common/consts';
import { getSortDirection } from '@Common/utils/getSortDirection.ts';
import { RunsTable } from '@Entities/runs/components/Table';
import { IRun } from '@Entities/runs/models';
import { runsQueries } from '@Entities/runs/queries';
import { useStreamStore } from '@Entities/stream/store';
import { DropDownRunsButton } from '@Features/runs/list/Dropdown.tsx';
import { adaptRunData } from '@Features/runs/list/helper';
import { useQuery } from '@tanstack/react-query';
import { TablePaginationConfig } from 'antd';
import type { FilterValue, SorterResult } from 'antd/lib/table/interface';
import { ReactElement, useCallback, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';

interface ISort {
    order_direction?: 'asc' | 'desc'
    order_by: string
}

export const RunsList = ({ search }: { search?: string }): ReactElement => {
    const streams = useStreamStore((state) => state.streams)
    const [searchParams, setSearchParams] = useSearchParams();
    const [sort, setSort] = useState<ISort | undefined>(undefined)
    const page = parseInt(searchParams.get('page') || '1', 10);
    const navigate = useNavigate()
    const { id } = useParams()

    const handleTableChange = (page: number) => {
        setSearchParams({
            page: String(page),
        });
    };

    const { data, isLoading } = useQuery(runsQueries.groupedRunList({
        project_id: id!,
        offset: (page - 1) * PAGINATION.PAGE_SIZE,
        limit: PAGINATION.PAGE_SIZE,
        search,
        order_by: sort?.order_by,
        order_direction: sort?.order_direction
    }, !!id))

    const tableData = adaptRunData(data, streams?.group_run_statistics)

    const handleRowClick = (id: string) => {
        navigate(`${id}`)
    }

    const handleChange = (
        _pagination: TablePaginationConfig,
        _filters: Record<string, FilterValue | null>,
        sorter: SorterResult<IRun>,
    ) => {
        if (!sorter?.field) {
            setSort(undefined)

            return
        }
        setSort({
            order_by: sorter?.field as string,
            order_direction: getSortDirection(sorter?.order)
        })
    }

    const renderDropdown = useCallback((record) => {
        return <DropDownRunsButton record={ record }/>
    }, [])

    return (
        <RunsTable
            data={ tableData }
            loading={ isLoading }
            /** @ts-ignore */
            onChange={ handleChange }
            onRow={ (record) => ({
                onClick: handleRowClick.bind(null, record.id)
            }) }
            pagination={ {
                current: page,
                pageSize: PAGINATION.PAGE_SIZE,
                total: data?.total,
                onChange: handleTableChange
            } }
            renderDropdown={ renderDropdown }
        />
    )
}
