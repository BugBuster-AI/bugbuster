import { ShortenedRecordTable } from '@Entities/records/components/ShortenedTable';
import { RecordTable } from '@Entities/records/components/Table';
import { recordQueries } from '@Entities/records/queries';
import { AddCaseButton } from '@Features/records/buttons/case-button.tsx';
import { DeleteButton } from '@Features/records/buttons/delete-button.tsx';
import { transformData, transformLongData } from '@Features/records/list/utils/transformData';
import { ShowRecord } from '@Features/records/show-record';
import { useQuery } from '@tanstack/react-query';
import { ReactElement } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';

interface IProps {
    isShortened?: boolean
}

export const RecordsList = ({ isShortened = false }: IProps): ReactElement => {
    const [searchParams, setSearchParams] = useSearchParams()
    const { id } = useParams()
    const { data } = useQuery(recordQueries.list({ projectId: id! }))

    if (isShortened) {
        const transformedData = transformData(data)

        return (
            <ShortenedRecordTable
                data={ transformedData }
                DeleteButton={ (props) => <DeleteButton recordId={ props.id }/> }
            />
        )
    }

    const transformedData = transformLongData(data)
    const isOpen = searchParams.get('recordId')

    const handleSearchParam = (id: string) => {
        if (!isOpen) {
            searchParams.set('recordId', id)
            setSearchParams(searchParams)
        } else {
            searchParams.delete('recordId')
            setSearchParams(searchParams)
        }
    }

    return (
        <>
            <RecordTable
                data={ transformedData }
                DeleteButton={ (props) => <DeleteButton recordId={ props.id }/> }
                OnHoverButton={ (props) => <AddCaseButton recordId={ props.id }/> }
                onRowClick={ (record) => handleSearchParam(record.id) }
            />

            {isOpen && <ShowRecord/>}
        </>

    )
}
