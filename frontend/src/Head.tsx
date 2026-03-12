import { VERSION } from '@Common/consts/env.ts';
import { Helmet } from 'react-helmet';
import { useTranslation } from 'react-i18next';

export const Head = () => {
    const { t } = useTranslation()

    const favicon = () => {
        switch (VERSION) {
            case 'ai':
                return '/favicon/screenmate.svg'

            case 'ru':
                return '/favicon/bugbuster.png'
            
            default:
                return
        }
    }

    return (
        // @ts-ignore
        <Helmet>
            <title>{t(`head.title.${VERSION}`)}</title>
            <link href={ favicon() } rel="icon" type="image/svg+xml"/>
        </Helmet>
    )
}
