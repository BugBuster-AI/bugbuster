interface IStepErrorTemplate {
    step: string;
    error: string
}

export const STEP_ERROR_TEMPLATE = ({ step, error }: IStepErrorTemplate) => {
    return `
Почему не сохраняется тест-кейс?
шаг: ${step}
текст ошибки: ${error}
    `
}

interface ICaseSaveErrorTemplate {
    error: string
}

export const CASE_SAVE_ERROR_TEMPLATE = ({ error }: ICaseSaveErrorTemplate) => {
    return `
Почему не сохраняется тест-кейс?
текст ошибки: ${error}
    `
}
