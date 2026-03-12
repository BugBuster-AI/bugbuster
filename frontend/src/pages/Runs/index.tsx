import { RunsDetailsPage, RunsListPage } from '@Pages/Runs/entities';
import { ReactElement } from 'react';
import { Route, Routes } from 'react-router-dom';

const RunsPage = (): ReactElement => {

    return <Routes>
        <Route element={ <RunsListPage /> } index />
        <Route element={ <RunsDetailsPage /> } path=":runId" />
    </Routes>
}

export default RunsPage
