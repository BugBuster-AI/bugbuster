import { EnvironmentListPage } from '@Pages/Environment/entities';
import { EnvironmentCreatePage } from '@Pages/Environment/entities/Create';
import { EnvironmentEditPage } from '@Pages/Environment/entities/Edit';
import { ReactElement } from 'react';
import { Route, Routes } from 'react-router-dom';

const EnvironmentPage = (): ReactElement => {

    return <Routes>
        <Route element={ <EnvironmentListPage /> } index />
        <Route element={ <EnvironmentCreatePage /> } path="create" />
        <Route element={ <EnvironmentEditPage /> } path="edit/:environmentId" />
    </Routes>
}

export default EnvironmentPage
