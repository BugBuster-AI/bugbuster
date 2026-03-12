import { Toolbar } from '@Common/components/Toolbar';
import { PATHS } from '@Common/consts';
import {  BaseLayout } from '@Components/BaseLayout';
import { LayoutTitle } from '@Components/LayoutTitle';
import { useProjectStore } from '@Entities/project/store';
import { variableQueries } from '@Entities/variable/queries';
import { DeleteVariableKit, EditVariableKit } from '@Features/variable';
import { CreateVariable } from '@Pages/Variables/entities/Details/components/CreateVariable';
import { VariableListTable } from '@Pages/Variables/entities/Details/components/VariableList';
import { useQueries } from '@tanstack/react-query';
import { Flex } from 'antd';
import get from 'lodash/get';
import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

export const VariableKitPage = () => {
    const { variableKitId } = useParams()
    const [search, setSearch] = useState('')

    const [kitData, variableListData] = useQueries({
        queries: [
            variableQueries.kitItem({ variables_kit_id: variableKitId! }, { enabled: !!variableKitId }),
            variableQueries.variableList({ variables_kit_id: variableKitId!, search }, { enabled: !!variableKitId }),
        ]
    })


    const project = useProjectStore((state) => state.currentProject)

    const backPath = project ? PATHS.VARIABLES.ABSOLUTE(project?.project_id!) : undefined

    const navigate = useNavigate()
    const handleSuccessDelete = () => {
        navigate(backPath || '-1')
    }

    const variableList = get(variableListData, 'data.variables_details', [])

    return (
        <Flex vertical>
            <LayoutTitle
                backPath={ backPath }
                loading={ kitData.isLoading }
                title={ kitData.data?.variables_kit_name }
                withBack
            />

            <Toolbar
                loading={ !kitData?.data }
                onSearch={ setSearch }
                renderButtons={ 
                    <>
                        <CreateVariable/>
                        {kitData?.data?.editable && <>
                            <EditVariableKit buttonProps={ { type: 'default' } } data={ kitData.data }/>
                            <DeleteVariableKit
                                buttonProps={ { type: 'default' } }
                                data={ kitData.data }
                                onSuccess={ handleSuccessDelete }
                            />
                        </>
                        }
                    </>
                }
            /> 
            

            <BaseLayout loading={ variableListData.isLoading }>
                <VariableListTable
                    data={ variableList }
                    error={ variableListData?.error || undefined }
                    isLoading={ variableListData.isLoading }
                />
            </BaseLayout>
        </Flex>
    )
}
