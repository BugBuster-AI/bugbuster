import { PlusOutlined } from '@ant-design/icons';
import { Button, ButtonProps, Modal, ModalProps } from 'antd';
import { forwardRef, MouseEvent, ReactElement, ReactNode, useImperativeHandle, useState } from 'react';

interface IProps {
    renderButton?: ({ onClick }: { onClick: () => void }) => ReactNode
    icon?: ReactNode
    buttonTitle?: string
    modalProps?: Omit<ModalProps, 'open'>
    buttonProps?: Omit<ButtonProps, 'icon'>
    children?: ReactElement
    closeAfterOk?: boolean
    renderContent?: ReactNode
    onOpenModal?: () => void
    needFixKeyDown?: boolean
}

export interface IModalRef {
    close: () => void
}

export const ModalButton =
    forwardRef<IModalRef, IProps>(({
        renderButton,
        icon = <PlusOutlined/>,
        modalProps,
        buttonProps,
        children,
        buttonTitle,
        closeAfterOk,
        renderContent,
        onOpenModal,
        needFixKeyDown,
    }, ref)
            : ReactElement => {
        const { onOk, ...restModalProps } = modalProps || {}
        const [open, setOpen] = useState<boolean>(false)

        const handleClose = (e: MouseEvent) => {
            e.stopPropagation()
            setOpen(false)
            modalProps?.onClose && modalProps?.onClose(e)
        }

        const handleClick = (e?: MouseEvent) => {
            e?.stopPropagation()
            e?.preventDefault()
            setOpen(true)
            onOpenModal?.()
        }

        const handleKeyDown = (e: React.KeyboardEvent) => {
            if (!needFixKeyDown) return
            if (e?.key?.toUpperCase() === 'ESCAPE') {
                return
            }

            e.stopPropagation()
        }

        const onConfirm = async (e: MouseEvent) => {
            if (onOk) {
                //@ts-ignore
                await onOk(e)
            }
            if (closeAfterOk) {
                setOpen(false)
            }
        }

        useImperativeHandle(ref, () => ({
            close: () => {
                setOpen(false)
            }
        }))

        return (
            <div onClick={ (e) => e.stopPropagation() }>
                {renderButton
                    ? renderButton({ onClick: handleClick })
                    :
                    <Button
                        icon={ icon }
                        onClick={ handleClick }
                        type={ 'primary' }
                        { ...buttonProps }
                    >
                        {buttonTitle}
                    </Button>
                }
                <Modal
                    destroyOnClose={ true }
                    modalRender={ (node) => <div onKeyDown={ handleKeyDown }>{node}</div> }
                    onCancel={ handleClose }
                    onOk={ onConfirm }
                    open={ open }
                    { ...restModalProps }
                >
                    {renderContent ? (open && renderContent) : children}
                </Modal>
            </div>
        )
    }
    )
