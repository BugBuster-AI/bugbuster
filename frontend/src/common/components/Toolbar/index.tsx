import { PlusOutlined } from '@ant-design/icons';
import { DebouncedSearch } from '@Components/DebouncedSearch';
import { Button, Flex, Input, theme } from 'antd';
import { ComponentProps, ReactElement, ReactNode } from 'react';

interface IProps {
    renderButtons?: ReactNode
    renderSearch?: ReactNode
    loading?: boolean
    addButton?: {
        title?: string
        props?: ComponentProps<typeof Button>
    } | null
    search?: {
        props?: ComponentProps<typeof Input>
    } | null

    onSearch?: (v: string) => void
}

const { useToken } = theme

export const Toolbar =
    ({ onSearch, loading = false, renderButtons, renderSearch, search = {}, addButton = {} }: IProps): ReactElement => {
        const { token } = useToken()

        return (
            <Flex
                align="center"
                gap={ token.marginXS }
                style={ {
                    background: token.colorBgBase,
                    padding: `${token.padding}px ${token.paddingXL}px`
                } }>
                    
                {loading ? '' :  <>
                    {renderButtons ? renderButtons : addButton && <Button
                        color="primary"
                        icon={ <PlusOutlined/> }
                        variant="solid"
                        { ...addButton?.props }
                    >
                        {addButton?.title}
                    </Button>}

                    {renderSearch ? renderSearch : search && (
                        <DebouncedSearch onChange={ onSearch }/>
                    )
                    }
                </>
                }
            </Flex>
        )
    }
