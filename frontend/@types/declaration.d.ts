/// <reference types="node" />
/// <reference types="vite-plugin-svgr/client" />

import {IWindowData} from "@Common/types";

declare module '*.svg' {
    import {FC, SVGProps} from 'react';
    const content: FC<SVGProps<SVGElement>>;
    export default content;
}

declare global {
    interface Window {
        widgetUserPayload?: any
        screenmate_app: IWindowData
    }
}

export {}
