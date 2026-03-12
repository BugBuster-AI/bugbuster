import { VariableType } from './types';

export interface IVariableKit {
    variables_kit_id: string;
    variables_kit_name: string;
    variables_kit_description: string;
    project_id: string;
    editable?: boolean
}

export interface IVariable {
    variable_name: string | null;
    computed_value: string | null;
    variable_details_id: string;  
    variable_description: string | null;
    variables_kit_id: string;

    variable_config: {
        type: keyof typeof VariableType | null;
        value: string | null
        base?: string
        utc_offset?: string
        shifts?: {
            value: number | string;
            unit: string
        }[]
        format?: string | null
        is_const?: boolean
    }
}
