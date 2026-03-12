import { MOBILE_MEDIA_QUERY } from '@Common/consts';
import { useLayoutEffect, useState } from 'react';

type IBreakpoints = boolean;

export const useMedia = (): IBreakpoints => {
    const [isMobile, setMobile] = useState<boolean>(false);

    useLayoutEffect(() => {
        const mql = window.matchMedia(MOBILE_MEDIA_QUERY);

        const handleResize = (event: MediaQueryListEvent | MediaQueryList): void => {
            setMobile(event.matches);
        }

        mql.addEventListener('change', handleResize);
        handleResize(mql);

        return () => mql.removeEventListener('change', handleResize);
    }, [])

    return isMobile
}

