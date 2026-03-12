import { Tag } from 'antd';

export const ImageTag = ({ children }: { children: string }) => {
    return (
        <Tag
            style={ {
                border: 'none',
                width: 'fit-content',
                borderBottomRightRadius: 0,
                borderBottomLeftRadius: 0
            } }
        >
            {children}
        </Tag>
    )
}
