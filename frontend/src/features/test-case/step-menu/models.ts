export type TAction = 'add' | 'clone' | 'delete' | 'add_result' | 'api_request';

export interface IMenuStep {
    step: string;
    type?: 'command' | 'expected' | 'api_request'; // Только для testCasesSteps
}

