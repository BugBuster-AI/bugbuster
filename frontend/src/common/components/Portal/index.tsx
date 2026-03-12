import { Fragment, ReactNode, RefObject, useEffect, useReducer } from 'react';
import { createPortal } from 'react-dom';

type PortalProps<T> = (
    | {
    containerRef?: RefObject<T>;
    containerQuerySelector?: never;
}
    | {
    containerQuerySelector?: string;
    containerRef?: never;
}
    ) & {
    children?: ReactNode;
};

export const Portal = <T extends Element>({ children, containerRef, containerQuerySelector }: PortalProps<T>) => {
    const [refreshKey, incrementRefreshKey] = useReducer((x: number) => x + 1, 0);

    useEffect(incrementRefreshKey, [incrementRefreshKey]);

    const querySelectorElement = containerQuerySelector ? document.querySelector(containerQuerySelector) : null;

    if ((containerQuerySelector && !querySelectorElement) || (containerRef && !containerRef?.current)) return null;
    
    return createPortal(
        <Fragment key={ refreshKey }>{children}</Fragment>,
        querySelectorElement ?? containerRef?.current ?? document.body,
    );
};
