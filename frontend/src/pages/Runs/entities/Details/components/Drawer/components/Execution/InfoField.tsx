import { Divider, Typography } from 'antd';


interface IInfoFieldProps {
    fieldName: any
    value?: string | null
    style?: React.CSSProperties
}


export function InfoField ({ fieldName, value, style }: IInfoFieldProps) {

    if (!value) return null

    return (
        <>
            <Divider orientation="left" orientationMargin={ 0 } style={ { marginBottom: 6, ...style } } plain>
                <Typography.Title level={ 5 }>
                    {fieldName}
                </Typography.Title>
            </Divider>
            <Typography.Text>
                {value}
            </Typography.Text>
        </>
    )
}
