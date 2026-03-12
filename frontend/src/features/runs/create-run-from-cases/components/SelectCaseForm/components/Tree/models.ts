import { ICaseWithExecution } from '@Features/runs/create-run-from-cases/store';

export interface IReturnTypeGetCases {
    cases: {
        [suiteId: string]: ICaseWithExecution[]
    }
    suiteKeys: string[]
}
