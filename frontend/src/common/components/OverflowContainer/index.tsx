import { ReactElement, cloneElement, useRef, useEffect, useState, useMemo } from 'react';

interface TEvents {
    isOverflow: boolean;
    isHover?: boolean
    originalHeight?: number
    element?: HTMLElement | null
}

export interface OverflowContainerProps {
    hoverable?: boolean
    children: ReactElement | ((events: TEvents) => ReactElement);
    onOverflowChange?: (events: TEvents) => void;
}

export const OverflowContainer = ({
    children,
    onOverflowChange,
    hoverable = false
}: OverflowContainerProps) => {
    const containerRef = useRef<HTMLElement>(null);
    const [isOverflow, setIsOverflow] = useState(false);
    const [isHover, setIsHover] = useState(hoverable ? false : undefined);
    const originalHeightRef = useRef<number | undefined>(undefined);

    const events = useMemo(() => ({
        isOverflow,
        isHover,
        originalHeight: originalHeightRef.current,
        element: containerRef.current
    } satisfies TEvents ), [isOverflow, isHover])

    useEffect(() => {
        const checkOverflow = () => {
            if (containerRef.current) {
                const element = containerRef.current;
                
                // Сохраняем оригинальную высоту только один раз при первой проверке
                if (originalHeightRef.current === undefined) {
                    originalHeightRef.current = element.scrollHeight;
                }
                
                const hasOverflowX = element.scrollWidth > element.clientWidth;
                const hasOverflowY = element.scrollHeight > element.clientHeight;
                const overflow = hasOverflowX || hasOverflowY;

                setIsOverflow(overflow);
                onOverflowChange?.(events);
            }
        };

        checkOverflow();

        const resizeObserver = new ResizeObserver(checkOverflow);

        if (containerRef.current) {
            resizeObserver.observe(containerRef.current);
        }

        return () => {
            resizeObserver.disconnect();
        };
    }, [children, onOverflowChange]);

    useEffect(() => {  
        if (!hoverable) return;
        
        const handleMouseEnter = () => setIsHover(true);
        const handleMouseLeave = () => setIsHover(false);
            
        if (containerRef.current) {
            const element = containerRef.current;
                
            element.addEventListener('mouseenter', handleMouseEnter);
            element.addEventListener('mouseleave', handleMouseLeave);
        }

        return () => {


            if (containerRef.current) {
                const element = containerRef.current;

                element.removeEventListener('mouseenter', handleMouseEnter);
                element.removeEventListener('mouseleave', handleMouseLeave);
            }
        }
        
    }, [hoverable])

    const childElement = typeof children === 'function' ? children(events) : children;

    return cloneElement(childElement, { ref: containerRef, 'data-overflow': isOverflow });
};
