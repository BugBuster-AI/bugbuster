import { type ReactElement } from 'react'
import SyntaxHighlighter from 'react-syntax-highlighter'
import { github } from 'react-syntax-highlighter/dist/esm/styles/hljs'

type TLanguage = 'javascript' | 'json'

interface IProps {
    code: string
    language: TLanguage
}

export function RunningStepSyntaxBlock ({ code, language }: IProps): ReactElement {
    return (
        <div
            style={ {
                borderRadius: 6,
                overflow: 'hidden',
                border: '1px solid rgba(0,0,0,0.06)',
            } }
        >
            <SyntaxHighlighter
                customStyle={ { margin: 0, fontSize: 12, padding: 10 } }
                language={ language }
                style={ github }
                wrapLongLines
            >
                {code}
            </SyntaxHighlighter>
        </div>
    )
}
