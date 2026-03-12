// Общий интерфейс степа для форм/иконок и тд
import { EStepGroup } from '@Entities/runs/models';
import { EStepType } from '@Entities/test-case/components/Form/models.ts';
import { ITestCaseStep } from '@Entities/test-case/models';
import { IExtraCaseType } from '@Entities/test-case/models/test-case-variables.ts';

type TApiStepData = Pick<ITestCaseStep, 'files' | 'method' | 'url' | 'headers' | 'data'>

export interface IStepFormData {
    isDeleteContextScreenshot?: boolean
}

/**
 * @description Локальный формат степов в кейсе
 * @prop string step - значение инпута
 * @prop [EStepType] type - тип инпута (api, step)
 * @prop [string] extraInfo - информация из validation_step - если есть
 * @prop [number] localIndex - общий локальный индекс (относительно массива из всех групп степов)
 * @prop [number] indexFor - если степ - проверка, то указывается индекс родительского степа
 * @prop [unknown] data - доп информация
 * @prop [IExtraCaseType] extraData - дополнительная информация из extra поля
 * @prop [TApiStepData] apiData - данные для API степов (опционально)
 * @prop [IStepFormData] tempFormData - данные формы для степа (если есть)
 */
export interface IStep {
    step: string;
    type?: EStepType;
    extraInfo?: string
    localIndex?: number
    originalIndex?: number
    indexFor?: number;
    data?: unknown
    extraData?: IExtraCaseType | null
    stepGroup?: EStepGroup

    // данные для (API степов)
    apiData?: TApiStepData
    tempFormData?: IStepFormData
}

export type TStepsVariants = 'before_browser_start' | 'before_steps' | 'steps' | 'after_steps'
