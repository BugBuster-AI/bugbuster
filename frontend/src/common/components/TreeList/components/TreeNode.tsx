import { LoadingOutlined } from '@ant-design/icons';
import { ITreeListItem } from '@Components/TreeList/models.ts';
import { Flex, Spin, Typography } from 'antd';
import { ReactElement, ReactNode } from 'react';

interface IProps {
    isLoading?: boolean
    record: ITreeListItem
    DropDown?: ReactNode
}

export const TreeNode = ({ isLoading, record, DropDown: DropDownComponent }: IProps): ReactElement => {
    const { count, title } = record || {}
    const getCount = (): string => {
        if (!count) return ''
        if (count > 99) {
            return '99+'
        }

        return String(count)
    }

    const resultCount = getCount()

    return (
        <Flex align="center" justify="space-between">
            {/*@ts-ignore}*/}
            <Typography style={ { paddingRight: '2px' } }>{title}</Typography>

            {isLoading ?
                <Spin indicator={ <LoadingOutlined spin/> } size="small"/> :

                <Flex gap={ 8 }>
                    {resultCount && <Typography>{resultCount}</Typography>}
                    {DropDownComponent}
                </Flex>
            }
        </Flex>
    )

}
