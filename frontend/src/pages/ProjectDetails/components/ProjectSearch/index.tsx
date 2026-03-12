import { PATHS } from '@Common/consts';
import { DebouncedSearch, IDebouncedSearchRef } from '@Components/DebouncedSearch';
import { useAuthStore } from '@Entities/auth/store/auth.store.ts';
import { projectQueries } from '@Entities/project/queries';
import { useProjectStore } from '@Entities/project/store';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { Flex, Select, Typography } from 'antd';
import filter from 'lodash/filter';
import map from 'lodash/map';
import split from 'lodash/split';
import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import styles from './ProjectSearch.module.scss'

export const ProjectSearch = () => {
    const [searchValue, setSearchValue] = useState('')
    const user = useAuthStore((state) => state.user)
    const [open, setOpen] = useState(false)
    const searchRef = useRef<IDebouncedSearchRef>(null)
    const project = useProjectStore((state) => state.currentProject)
    const { data, isFetching } = useQuery({
        ...projectQueries.list(user?.active_workspace_id, { search: searchValue }),
        placeholderData: keepPreviousData
    })

    const navigate = useNavigate()
    const location = useLocation()

    const handleResetSearch = () => {
        searchRef?.current?.clear()
        setSearchValue('')
    }

    const handleSelect = (projectId: string) => {
        const routePath = filter(split(location.pathname, '/'), Boolean)[2]

        navigate(`${PATHS.PROJECT.ABSOLUTE(projectId)}/${routePath}`)
    }

    useEffect(() => {
        if (!open) {
            handleResetSearch()
        }
    }, [open]);


    if (!project) {
        return null
    }

    return (
        <Select
            defaultValue={ project?.project_id }
            dropdownRender={ (menu) =>
                (<Flex gap={ 4 } vertical>
                    <DebouncedSearch
                        ref={ searchRef }
                        loading={ isFetching }
                        onChange={ setSearchValue }
                        width={ 'auto' }
                    />
                    {menu}
                </Flex>) }
            labelRender={ () =>
                <Typography.Text
                    style={ { fontWeight: 700 } }
                >
                    {project?.name}
                </Typography.Text>
            }
            onDropdownVisibleChange={ setOpen }
            onSelect={ handleSelect }
            // open={ open }
            options={ map(data, (item) => ({
                label: item.name,
                value: item.project_id
            })) }
            rootClassName={ styles.selectWrapper }
            style={ { padding: '0!important', border: '3px solid red!important' } }
            value={ project?.project_id }
            variant={ 'borderless' }
        />
    )
}
