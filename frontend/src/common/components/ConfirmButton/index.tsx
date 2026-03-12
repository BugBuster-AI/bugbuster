import { DeleteOutlined } from '@ant-design/icons';
import { Button, ButtonProps, Modal, ModalProps } from 'antd';
import { MouseEvent, ReactElement, ReactNode, useState } from 'react';

interface IProps {
    renderButton?: ({ onClick }: { onClick: () => void }) => ReactNode
    icon?: ReactNode
    modalProps?: Omit<ModalProps, 'open'>
    buttonProps?: Omit<ButtonProps, 'icon'>
    children?: ReactElement
    closeAfterOk?: boolean
    buttonLabel?: string
}

export const ConfirmButton =
    ({ renderButton, icon = <DeleteOutlined/>, buttonLabel, modalProps, buttonProps, children, closeAfterOk }: IProps):
        ReactElement => {
        const [isLoading, setLoading] = useState(false)
        const { onOk, ...restModalProps } = modalProps || {}
        const [open, setOpen] = useState<boolean>(false)

        const handleClose = (e: MouseEvent) => {
            e.stopPropagation()
            setOpen(false)
        }

        const handleClick = (e?: MouseEvent) => {
            e?.stopPropagation()
            setOpen(true)
        }

        const handleOk = async (e: MouseEvent) => {

            if (onOk) {
                try {
                    setLoading(true)
                    //@ts-ignore
                    await onOk(e)
                    setLoading(false)
                } catch {

                    return
                }
            }
            if (closeAfterOk) {
                setOpen(false)
            }
        }

        return <div onClick={ (e) => e.stopPropagation() }>
            {
                renderButton
                    ? renderButton({ onClick: handleClick })
                    :
                    <Button
                        icon={ icon }
                        loading={ isLoading }
                        onClick={ handleClick }
                        type={ 'text' }
                        { ...buttonProps }
                    >{buttonLabel}</Button>
            }
            <Modal onCancel={ handleClose } onOk={ handleOk } open={ open } { ...restModalProps } >{children}</Modal>
        </div>
    }
