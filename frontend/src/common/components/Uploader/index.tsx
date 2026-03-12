import { DraggerProps, Upload, UploadFile, UploadProps } from 'antd';
import { UploadChangeParam } from 'antd/es/upload';
import { ReactNode, useMemo } from 'react';

interface IProps {
    children: ReactNode
    onDropFile?: (files: File[]) => void;
    disabled?: boolean
    defaultFileList?: File[]
}

interface IDefaultProps extends IProps {
    type: 'default'
    props?: UploadProps
}

interface IDraggerProps extends IProps {
    type: 'dragger'
    props?: DraggerProps
}

type IUploaderProps = IDefaultProps | IDraggerProps

export const Uploader =
    ({ type, disabled = false, children, defaultFileList, onDropFile, ...rest }: IUploaderProps) => {
        const Component = type === 'dragger' ? Upload.Dragger : Upload;

        const handleChange = (info: UploadChangeParam) => {
            const files = info.fileList
                .map((file: UploadFile) => file.originFileObj)
                //@ts-ignore
                .filter((file): file is File => !!file);

            //@ts-ignore
            onDropFile?.(files);
        };

        const defaultFiles = useMemo(() => defaultFileList?.map((file: File, index: number) => ({
            uid: String(index),
            name: file.name,
            status: 'done',
            url: URL.createObjectURL(file),
        })), [defaultFileList]);

        return (
            <Component
                accept={ '.jpeg,.png,.jpg,.svg' }
                beforeUpload={ () => {
                    return false;
                } }
                defaultFileList={ defaultFiles as UploadFile[] }
                disabled={ disabled }
                onChange={ (info) => {
                    handleChange(info);
                    rest.props?.onChange?.(info);
                } }
                showUploadList={ {
                    showRemoveIcon: !disabled,
                } }
            >
                {children}
            </Component>
        )
    }
