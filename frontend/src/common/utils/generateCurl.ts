import { EContentType, getContentType } from '@Common/utils/curl';
import { objectToHar } from '@Common/utils/har';
import fetchToCurl from 'fetch-to-curl';
import { HTTPSnippet } from 'httpsnippet-lite';
import cloneDeep from 'lodash/cloneDeep';
import head from 'lodash/head';
import isArray from 'lodash/isArray';
import isEmpty from 'lodash/isEmpty';
import isString from 'lodash/isString';

interface IRequestOptions {
    url: string;
    body?: Record<string, unknown> | string;
    headers?: Record<string, string>;
    method: string;
}

function decodeCurlTemplates (curlString: string): string {
    // Регулярное выражение для поиска %7B%7B...%7D%7D конструкций
    const pattern = /%7B%7B(.*?)%7D%7D/g;

    return curlString.replace(pattern, (_, innerText) => {
        // Заменяем %7B на { и %7D на } во внутреннем тексте
        const decodedInner = innerText
            .replace(/%7B/g, '{')
            .replace(/%7D/g, '}');

        return `{{${decodedInner}}}`;
    });
}

async function generateCurl (initialOptions: IRequestOptions): Promise<string> {
    const ContentType = getContentType(initialOptions.headers, false) || undefined

    const options = cloneDeep(initialOptions)

    console.log(initialOptions, 'MIME TYPE')

    let postData: any = {
        mimeType: ContentType,
    };

    // Обработка x-www-form-urlencoded
    if (ContentType === EContentType.URLENCODED && options.body && typeof options.body === 'object') {
        postData.params = objectToHar(options.body as Record<string, string>);
    }
    // Обработка form-data
    else if (ContentType === EContentType.FORM_DATA && options.body && typeof options.body === 'object') {
        postData.params = objectToHar(options.body as Record<string, string>);
    }

    // Обработка JSON и других типов
    else {
        const formattedBody = typeof options.body === 'string'
            ? options.body
            : isEmpty(options.body) ? null : JSON.stringify(options.body);

        postData.text = formattedBody;
    }

    if (options.method === 'GET') {
        options?.headers && delete options.headers['Content-Type'];
    }

    //@ts-ignore
    const snippet = new HTTPSnippet({
        url: options.url,
        method: options.method,
        headers: objectToHar(options.headers),
        postData: postData,
    });


    const curlResolve = await snippet.convert('shell', 'curl', {});

    if (isString(curlResolve)) {
        return decodeCurlTemplates(curlResolve.replace(/(\r\n|\n|\r)/g, ''));
    }

    if (isArray(curlResolve)) {
        const headCurl = head(curlResolve) as string;

        if (headCurl.startsWith('curl ')) {
            return headCurl.replace(/(\r\n|\n|\r)/g, '');
        }
    }

    // Запасной вариант
    const formattedBody = typeof options.body === 'string'
        ? options.body
        : JSON.stringify(options.body);

    const rawCurl = fetchToCurl({
        url: options.url,
        body: formattedBody,
        headers: options.headers as unknown as Record<string, string>,
        method: options.method as 'GET' || 'GET',
    });

    return rawCurl.replace(/(\r\n|\n|\r)/g, '');
}

export { generateCurl };
