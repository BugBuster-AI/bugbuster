/// <reference types="node" />
/// <reference types="vite-plugin-svgr/client" />
/// <reference types="vite/client" />

declare module '*.svg' {
    import {FC, SVGProps} from 'react';
    const content: FC<SVGProps<SVGElement>>;
    export default content;
}

interface ImportMeta {
    readonly env: ImportMetaEnv
}
