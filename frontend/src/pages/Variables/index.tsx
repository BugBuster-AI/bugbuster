import { VariableKitPage } from '@Pages/Variables/entities/Details';
import { Route, Routes } from 'react-router-dom';
import { VariablesListPage } from './entities'

export default function VariablesPage () {
    return (
        <Routes>
            <Route element={ <VariablesListPage/> } index/>
            <Route element={ <VariableKitPage/> } path=":variableKitId"/>
        </Routes>
    )
}
