const { compress, decompress } = require('json-url')('lzma');

const createHash = async (params: Record<string, unknown>) => {
    return compress(params)
}

const decodeHash = async (hash: string) => {
    await decompress(hash)
}

export {
    createHash,
    decodeHash
}
