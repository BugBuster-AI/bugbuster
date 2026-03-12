export const getSortableKey = ({ index, prefix }: { index: number, prefix: string }) => {
    return [index, prefix].join('_')
}
