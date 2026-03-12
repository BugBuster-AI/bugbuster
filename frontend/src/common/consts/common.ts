/* Дефолтные значения пагинации */
export const PAGINATION = {
    PAGE_SIZE: 5,
    PAGE: 1,
    PAGE_SIZE_OPTIONS: ['5', '10', '20']
}

/* Размер картинок */
export const DEFAULT_IMAGE_SIZE = {
    SMALL: {
        width: 250,
        height: 180
    }
}

/** Типы для драг-н-дропа */
export const DragTypes = {
    DRAGGABLE_CASE: 'draggable_case'
}

export const DragOverTypes = {
    SUITE: 'suite',
}

export const DragCaseEvents = {
    DRAG_START: 'case_drag_start',
    DRAG_END: 'case_drag_end'
}

export const COMMON_SEARCH_PARAMS = {
    PAGE: 'page',
    BACK_STATE: 'back',
    BACK_URL: 'backUrl'
}


export const API_METHODS = [
    'GET',
    'POST',
    'PUT',
    'DELETE',
    'PATCH',
    'HEAD',
    'OPTIONS'
]

export const VALIDATION_TYPES = [
    '=',
    '!=',
    '>',
    '<',
    '>=',
    '<=',
    'IN',
    'NOT IN',
    'LIKE'
]

export const METHOD_COLORS = {
    GET: 'rgba(0, 193, 61, 1)',
    POST: 'rgba(254, 154, 0, 1)',
    PUT: 'rgba(9, 88, 217, 1)',
    DELETE: 'rgba(251, 44, 54, 1)',
    PATCH: 'rgba(83, 29, 171, 1)',
    HEAD: 'rgba(8, 151, 156, 1)',
    OPTIONS: 'rgba(196, 29, 127, 1)'
}
