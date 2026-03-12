import { Route, Routes } from 'react-router-dom';
import { SharedStepsCreatePage, SharedStepsEditPage, SharedStepsListPage } from './entities';

export default function SharedStepsPage () {
    return (
        <Routes>
            <Route element={ <SharedStepsListPage/> } index/>
            <Route element={ <SharedStepsCreatePage/> } path="create"/>
            <Route element={ <SharedStepsEditPage/> } path="edit/:sharedStepId"/>
        </Routes>
    )
}
