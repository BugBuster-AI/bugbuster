import { useProjectStore } from '@Entities/project/store';
import { recordQueries } from '@Entities/records/queries';
import { useShowRecordStore } from '@Features/records/show-record/store';
import { useQuery } from '@tanstack/react-query';
import head from 'lodash/head';
import { useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';

export const useShowRecordData = () => {
    const [searchParams] = useSearchParams()
    const recordId = searchParams.get('recordId')
    const setRecord = useShowRecordStore((state) => state.setRecord)
    const setLoading = useShowRecordStore((state) => state.setLoading)
    const setError = useShowRecordStore((state) => state.setError)
    const project = useProjectStore((state) => state.currentProject)

    const { data, isLoading, isError } = useQuery(recordQueries.showFull({
        happy_pass_id: recordId!!,
        project_id: project?.project_id!
    }, !!recordId && !!project?.project_id))

    useEffect(() => {
        if (data) {
            const headData = head(data?.items || [])

            setRecord(headData!!)
        }
    }, [data]);

    useEffect(() => {
        setLoading(isLoading)

        if (isError) {
            setError('Error fetching record data')
        } else {
            setError(undefined)
        }

    }, [isLoading, isError]);

    return { data, isLoading, isError }
}
