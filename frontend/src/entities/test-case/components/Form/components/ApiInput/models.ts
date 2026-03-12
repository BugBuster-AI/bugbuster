// объект который мы получаем отправляем на бэк
import { EContentType } from '@Common/utils';
import { JSONOutput } from 'curlconverter';

export interface ICurlObject {
    url?: string;
    headers?: Record<string, unknown>;
    params?: Record<string, unknown>
    // Data
    data?: Record<string, unknown> | string;
    // Files
    files?: Record<string, unknown>
    // Content Type
    contentType?: EContentType | null
    method?: string
}

// объект, который мы получаем на фронте
export interface ICurlConvertedObject extends JSONOutput {
    /*
     * data: Record<string, string>
     * headers: Record<string, string>
     * files: Record<string, string>
     * queries: Record<string, string>
     * method: string;
     * raw_url: string;
     * url: string;
     */
}
