import { CopyOutlined } from '@ant-design/icons';
import { asyncHandler } from '@Common/utils';
import { ITestCase } from '@Entities/test-case/models';
import { useCopyCase } from '@Entities/test-case/queries';
import { Button } from 'antd';
import { ReactElement } from 'react';

interface IProps {
    case_id: string[]
    onClick?: () => void
    disabled?: boolean,
    onSuccess?: (data: ITestCase[]) => void
}

export const CopyButton = ({ case_id, onClick, disabled = false, onSuccess }: IProps): ReactElement => {
    const { mutateAsync, isPending } = useCopyCase()

    const handleClick = async () => {
        if (disabled) return

        if (onClick) {
            onClick()

            return
        }

        await asyncHandler(mutateAsync.bind(null, case_id), {
            onSuccess: (data) => {
                if (onSuccess) {
                    onSuccess(data)
                }
            }
        })

    }

    return <Button disabled={ disabled } icon={ <CopyOutlined/> } loading={ isPending } onClick={ handleClick }/>

}
