import { ITestCase } from '@Entities/test-case/models';

export interface ISuite {
    name: string;
    description: string;
    suite_id: string;
    parent_id: string;
    cases: ITestCase[]
    children?: ISuite[];
    position: number
}

export interface IUserTree {
    name: string;
    description: string;
    project_id: string;
    suites: ISuite[]
}

export interface IUpdateSuite {
    suite_id: string;
    parent_id?: string | null;
    name?: string;
    description?: string;
    new_position?: number
}

// Интерфейс данных для получения дерева сьютов
export interface IUserTreePayload {
    project_id?: string;
    suite_id?: string | null
    filter_cases?: string
}

// Интерфейс данных при создании сьюта
export interface ICreateSuitePayload {
    name: string;
    description: string;
    project_id: string;
    parent_id?: string | null;
}

export interface IChangeSuitePosition {
    suite_id: string;
    new_position: number
}
