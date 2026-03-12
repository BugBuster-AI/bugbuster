import { ISuite, IUserTree } from '@Entities/suite/models';
import { suiteQueries } from '@Entities/suite/queries';
import { useSuiteStore } from '@Entities/suite/store';
import { useQuery, UseQueryResult } from '@tanstack/react-query';
import head from 'lodash/head';
import { useEffect } from 'react';
import { useParams } from 'react-router-dom';

type ReturnType = UseQueryResult<IUserTree[]>

const searchSuites = (suites: ISuite[], id: string): ISuite | undefined => {
    let result: ISuite | undefined = undefined;

    const search = (suites: ISuite[]) => {
        for (const suite of suites) {
            if (suite.suite_id === id) {
                result = suite;
            }
            if (suite.children) {
                search(suite.children);
            }
        }
    };

    search(suites);

    return result;
};

export const useSuiteControl = (): ReturnType => {
    const { id: projectId } = useParams()
    const setLoading = useSuiteStore((state) => state.setLoading)
    const setSuite = useSuiteStore((state) => state.setSuite)
    const selectedSuite = useSuiteStore((state) => state.selectedSuite)
    const searchValue = useSuiteStore((state) => state.searchValue)

    const {
        isLoading,
        ...data
    } = useQuery(suiteQueries.userTree({ project_id: projectId, filter_cases: searchValue }, !!projectId))

    useEffect(() => {
        if (selectedSuite && data?.data) {
            const headTree = head(data.data);

            if (headTree) {
                const suite = searchSuites(headTree.suites || [], selectedSuite.suite_id);

                if (suite) {
                    setSuite(suite);
                }
            }
        }
    }, [selectedSuite, data?.data, setSuite]);

    useEffect(() => {
        setLoading(isLoading)
    }, [isLoading]);

    useEffect(() => {
        return () => {
            setSuite(null)
            setLoading(false)
        }
    }, []);

    return { isLoading, ...data } as ReturnType
}
