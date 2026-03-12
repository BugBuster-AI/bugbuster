import { EditOutlined } from '@ant-design/icons';
import { encodeParams } from '@Common/utils/transformQueryParams.ts';
import { Button } from 'antd';
import { ReactElement } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

interface IProps {
    case_id: string;
    thisTab?: boolean
}

export const EditCaseButton = ({ case_id, thisTab }: IProps): ReactElement => {
    const navigate = useNavigate()
    const [searchParams] = useSearchParams()

    const handleClick = () => {
        if (thisTab) {
            const back = searchParams.toString()
            const backState = encodeParams(back.toString())
            let url = `edit/${case_id}`

            if (backState) {
                url += `?back=${backState}`
            }
            navigate(url)

            return
        }
        window.open(`repository/edit/${case_id}`, '_blank')
    }

    return <Button icon={ <EditOutlined/> } onClick={ handleClick }/>
}
