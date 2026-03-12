import { AnimatePresence, motion } from 'framer-motion';
import { ReactNode, CSSProperties } from 'react'

interface IProps {
    trigger?: ReactNode
    children: ReactNode
    visible?: boolean
    config?: {
        duration: number
    }
    style?: CSSProperties
    className?: string
    saveInDom?: boolean
}

export const AppearanceAnimation = ({ 
    saveInDom, style, className, children, trigger, visible, config }: IProps) => {


    const content = saveInDom ? (
        <>  {trigger}
            <motion.div
                animate={ { height: visible ? 'auto' : 0, opacity: visible ? 1 : 0 } }

                exit={ { height: 0, opacity: 0 } }
                initial={ { height: 0, opacity: 0 } }
                style={ { overflow: 'hidden' } }
                transition={ { duration: config?.duration ?? .3, ease: 'easeInOut' } }
            >
                {children}
            </motion.div>
        </>) : 
        <>
            {trigger}
            <AnimatePresence>
                {visible && (
                    <motion.div
                        animate={ { height: 'auto', opacity: 1 } }
                        exit={ { height: 0, opacity: 0 } }
                        initial={ { height: 0, opacity: 0 } }
                        style={ { overflow: 'hidden' } }
                        transition={ { duration: config?.duration ?? .3, ease: 'easeInOut' } }
                    >
                        {children}
                    </motion.div>
                )
                }
            </AnimatePresence>
        </>

    if (style || className) {
        return <div className={ className } style={ { ...style } }>{content}</div>
    }

    return content
}
