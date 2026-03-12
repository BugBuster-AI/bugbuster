import { PATHS } from '@Common/consts';
import { PageLayout } from '@Common/layouts';
import { ProtectedRoute } from '@Components/ProtectedRoute';
import { GoogleCallback } from '@Pages/Auth/entities/Google';
import { SharedSteps } from '@Pages/index.ts';
import { Spin } from 'antd';
import { Suspense, lazy, ReactElement } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';

const AcceptInvite = lazy(() => import('@Pages/AcceptInvite'))
const AuthPage = lazy(() => import('@Pages/Auth'))
const MainPage = lazy(() => import('@Pages/Main'))
const ProjectPage = lazy(() => import('@Pages/ProjectDetails'))
const RepositoryPage = lazy(() => import('@Pages/Repository'))
const RunsPage = lazy(() => import('@Pages/Runs'))
const RecordsPage = lazy(() => import('@Pages/Records'));
const EnvironmentPage = lazy(() => import('@Pages/Environment'))
const WorkspacePage = lazy(() => import('@Pages/Workspace'))
const RunningCase = lazy(() => import('@Pages/RunningCase'));
const ConfirmReset = lazy(() => import(`@Pages/ConfirmReset`))
const VariablesPage = lazy(() => import(`@Pages/Variables`))

export const SuspenseFallback = () => <Spin fullscreen/>;

const ProtectedRouteWithSuspense = ({
    type,
    children,
}: {
    type: 'public' | 'private';
    children: React.ReactNode;
}) => (
    <ProtectedRoute type={ type }>
        <Suspense fallback={ <SuspenseFallback/> }>{children}</Suspense>
    </ProtectedRoute>
);

const AppRoutes = (): ReactElement => (

    <Routes>
        <Route element={ <GoogleCallback/> } path={ PATHS.AUTH.GOOGLE.ABSOLUTE }/>
        <Route element={ <ConfirmReset/> } path={ PATHS.AUTH.CONFIRM_RESET.ABSOLUTE }/>

        <Route
            element={
                <Suspense fallback={ <SuspenseFallback/> }>
                    <AcceptInvite/>
                </Suspense>
            }
            path="accept-invite"
        />

        <Route
            element={
                <ProtectedRouteWithSuspense type="private">
                    <RunningCase/>
                </ProtectedRouteWithSuspense>
            }
            path="running/:runId"
        />

        <Route
            element={
                <ProtectedRouteWithSuspense type="public">
                    <AuthPage/>
                </ProtectedRouteWithSuspense>
            }
            path="auth/*"
        />

        <Route
            element={
                <ProtectedRoute type="private">
                    <PageLayout/>
                </ProtectedRoute>
            }
            path="/"
        >
            <Route
                element={
                    <Suspense fallback={ <SuspenseFallback/> }>
                        <MainPage/>
                    </Suspense>
                }
                index
            />

            <Route
                element={
                    <Suspense fallback={ <SuspenseFallback/> }>
                        <ProjectPage/>
                    </Suspense>
                }
                path="project/:id"
            >
                <Route
                    element={ <RepositoryPage/> }
                    path="repository/*"
                />
                <Route
                    element={ <RunsPage/> }
                    path="runs/*"
                />
                <Route
                    element={ <RecordsPage/> }
                    path="records"
                />
                <Route
                    element={ <EnvironmentPage/> }
                    path="environments/*"
                />
                <Route
                    element={ <SharedSteps/> }
                    path="shared_steps/*"
                />
                <Route
                    element={ <VariablesPage/> }
                    path="variables/*"
                />
                <Route element={ <Navigate to="repository"/> } index/>
            </Route>
            <Route
                element={
                    <Suspense fallback={ <SuspenseFallback/> }>
                        <WorkspacePage/>
                    </Suspense>
                }
                path="/*"
            />
        </Route>
    </Routes>

);

export default AppRoutes;
