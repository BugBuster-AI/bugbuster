import { HighlightTextarea } from '@Components/HighlightTextarea';
import { variableQueries } from '@Entities/variable/queries';
import { useQuery } from '@tanstack/react-query';
import map from 'lodash/map';
import { ComponentProps } from 'react';

interface IProps extends ComponentProps<typeof HighlightTextarea> {
    variablesKitName?: string
    projectId?: string
    externalVariables?: string[]
}

export const AutocompleteVariablesTextarea = ({
    variablesKitName,
    projectId,
    externalVariables,
    ...props
}: IProps) => {
    const { data: variablesList } = useQuery(variableQueries.variableListByName({
        project_id: projectId!!,
        variables_kit_name: variablesKitName!!,
    }, { enabled: !!variablesKitName && !!projectId && !externalVariables }))

    const formattedList = externalVariables ?? map(variablesList?.variables_details, (item) => item.variable_name ?? '')

    return <HighlightTextarea
        initialVariables={ formattedList || [] }
        style={ { wordBreak: 'break-word' } }
        { ...props }
    />
}
