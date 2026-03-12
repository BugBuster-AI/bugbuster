export const decodeParams = (search: string) => {
    return atob(search)
}

export const encodeParams = (search: string) => {
    return btoa(search)
}
