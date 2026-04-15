import { Copy, Maximize2, Minimize2 } from 'lucide-react';
import type { ReactElement } from 'react';

/** Размер как у иконок в `Button` Ant Design `size="small"` */
const TOOLBAR_ICON_PX = 14

const toolbarIconProps = {
    'aria-hidden': true,
    size: TOOLBAR_ICON_PX,
    strokeWidth: 2,
} as const

/** [copy](https://lucide.dev/icons/copy) — копирование лога и кода */
export function CodegenCopyIcon (): ReactElement {
    return <Copy { ...toolbarIconProps }/>
}

/** Иконка «развернуть» — [maximize-2](https://lucide.dev/icons/maximize-2) */
export function CodegenExpandLayoutIcon (): ReactElement {
    return <Maximize2 { ...toolbarIconProps }/>
}

/** Иконка «свернуть» — [minimize-2](https://lucide.dev/icons/minimize-2) */
export function CodegenCollapseLayoutIcon (): ReactElement {
    return <Minimize2 { ...toolbarIconProps }/>
}
