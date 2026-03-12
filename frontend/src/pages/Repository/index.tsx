import { useTestCaseStore } from '@Entities/test-case';
import { CreateCasePage, SuitesPage } from '@Pages/Repository/entities';
import { EditCasePage } from '@Pages/Repository/entities/EditCase';
import { ReactElement, useEffect } from 'react';
import { Route, Routes } from 'react-router-dom';

const RepositoryPage = (): ReactElement => {
    const setCurrentCase = useTestCaseStore((state) => state.setCurrentCase)

    useEffect(() => {
        return () => {
            setCurrentCase(undefined)
        }
    }, []);

    return (
        <Routes>
            <Route element={ <SuitesPage/> } index/>
            <Route element={ <CreateCasePage/> } path="/create-case"/>
            <Route element={ <EditCasePage/> } path="/edit/:caseId"/>
        </Routes>
    )
}

export default RepositoryPage
