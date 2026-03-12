/* eslint max-lines: "off" */

import { CLASSNAMES } from '@Common/consts/css';
import { formatVariableToComponent } from '@Common/utils/formatVariable.tsx';
import { Dropdown } from 'antd';
import type { DropdownProps } from 'antd';
import cn from 'classnames';
import {
    Editor,
    EditorState,
    ContentState,
    CompositeDecorator,
    Modifier,
    SelectionState,
    getVisibleSelectionRect
} from 'draft-js';
import React, { useEffect, useState, useRef, forwardRef, useImperativeHandle, useMemo } from 'react';
import 'draft-js/dist/Draft.css';
import styles from './HighlightTextarea.module.scss'

// Стратегия для поиска паттернов переменных {{...}}
const findVariableEntities = (contentBlock, callback) => {
    const text = contentBlock.getText();
    const regex = /\{\{[^}]+\}\}/g;
    let match;

    while ((match = regex.exec(text)) !== null) {
        callback(match.index, match.index + match[0].length);
    }
};

// Компонент для подсветки переменных
const VariableSpan = (props) => {
    return formatVariableToComponent(props.children)
};

interface IHighlightTextareaProps {
    disableLineBreak?: boolean
    disableAutoComplete?: boolean
    value?: string;
    onChange?: (value: string) => void;
    placeholder?: string;
    style?: React.CSSProperties;
    className?: string;
    id?: string;
    name?: string;
    disabled?: boolean;
    autoFocus?: boolean;
    onBlur?: (e: React.FocusEvent<any>) => void;
    onFocus?: (e: React.FocusEvent<any>) => void;
    status?: '' | 'error' | 'warning'; // For Ant Design form validation status
    autoSize?: boolean | { minRows?: number; maxRows?: number };
    bordered?: boolean;
    maxLength?: number;
    allowClear?: boolean;
    onClick?: () => void;
    renderInBody?: boolean
    initialVariables?: string[]
}


export const HighlightTextarea = forwardRef<any, IHighlightTextareaProps>(({
    value = '',
    disableLineBreak,
    disableAutoComplete,
    onChange,
    placeholder,
    style,
    renderInBody = false,
    className,
    id,
    disabled = false,
    onBlur,
    onFocus,
    status,
    autoSize,
    bordered = true,
    maxLength,
    onClick,
    allowClear = false,
    initialVariables = []
}, ref) => {
    // Создаем декоратор для подсветки переменных
    const decorator = useMemo(() => new CompositeDecorator([{
        strategy: findVariableEntities,
        component: VariableSpan,
    }]), []);

    const [editorState, setEditorState] = useState(() =>
        EditorState.createWithContent(
            ContentState.createFromText(value || ''),
            decorator
        )
    );

    const [dropdownVisible, setDropdownVisible] = useState(false);
    const [filteredVariables, setFilteredVariables] = useState<string[]>([]);
    const [selectedIndex, setSelectedIndex] = useState(0);
    const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0 });
    const [isFocused, setIsFocused] = useState(false);
    const [isHovered, setIsHovered] = useState(false);
    const editorRef = useRef<HTMLDivElement>(null);
    const internalEditorRef = useRef<Editor>(null);
    const wrapperRef = useRef<HTMLDivElement>(null);

    // Реф для отслеживания процесса закрытия дропдауна
    const isClosingDropdown = useRef(false);

    // Реф для хранения текущего значения чтобы избежать бесконечных обновлений
    const currentValueRef = useRef(value);

    // Состояние для хранения переменных и флага загрузки
    const [variables, setVariables] = useState<string[]>(initialVariables);
    const variablesLoaded = useRef(false);

    // Функция для обновления контента редактора
    const updateEditorContent = (newValue: string) => {
        const newContentState = ContentState.createFromText(newValue || '');
        const newEditorState = EditorState.createWithContent(newContentState, decorator);

        setEditorState(newEditorState);
        currentValueRef.current = newValue;
    };

    // Экспортируем методы для Form
    useImperativeHandle(ref, () => ({
        focus: () => {
            internalEditorRef.current?.focus();
            setIsFocused(true);
        },
        blur: () => {
            if (internalEditorRef.current) {
                const editorNode = document.querySelector(`[data-editor-id="${id}"]`);

                if (editorNode) {
                    (editorNode as HTMLElement).blur();
                    setIsFocused(false);
                }
            }
        },
        getValue: () => {
            return editorState.getCurrentContent().getPlainText();
        },
        setValue: (newValue: string) => {
            updateEditorContent(newValue);
        }
    }));

    // Обновляем editorState только когда значение реально изменилось
    useEffect(() => {
        if (value !== currentValueRef.current) {
            updateEditorContent(value);
        }
    }, [value, decorator]);

    const handleChange = (newState: EditorState) => {
        // Проверяем maxLength, если он задан
        if (maxLength !== undefined) {
            const newText = newState.getCurrentContent().getPlainText();

            if (newText.length > maxLength) {
                return; // Не позволяем ввод больше maxLength
            }
        }

        // Сначала обновляем состояние редактора
        setEditorState(newState);

        const newText = newState.getCurrentContent().getPlainText();

        // Обновляем реф текущего значения
        currentValueRef.current = newText;

        // Вызываем внешний обработчик onChange если он есть
        if (onChange) {
            onChange(newText);
        }

        // Не обрабатываем логику дропдауна, если он закрывается
        if (isClosingDropdown.current) {
            return;
        }

        const selection = newState.getSelection();
        const content = newState.getCurrentContent();
        const block = content.getBlockForKey(selection.getStartKey());
        const text = block.getText();
        const cursorPosition = selection.getStartOffset();

        // Проверяем, печатается ли переменная
        let isTypingVariable = false;
        let variableStart = -1;
        let partialVariable = '';

        // Проверяем, только что закрыли переменную "}}"
        const hasClosedVariable = cursorPosition >= 2 &&
            text.substring(cursorPosition - 2, cursorPosition) === '}}';

        if (hasClosedVariable) {
            setDropdownVisible(false);
        } else {
            // Проверяем, есть ли открытая переменная (между {{ и курсором нет }})
            for (let i = cursorPosition - 1; i >= 0; i--) {
                if (text.substring(i, i + 2) === '{{') {
                    // Проверяем, есть ли закрывающие скобки между {{ и курсором
                    const textBetween = text.substring(i, cursorPosition);

                    if (!textBetween.includes('}}')) {
                        isTypingVariable = true;
                        variableStart = i + 2;
                        partialVariable = text.substring(variableStart, cursorPosition);
                    }
                    break;
                }
                // Если встретили закрывающие скобки до открывающих, выходим
                if (i > 0 && text.substring(i - 1, i + 1) === '}}') {
                    break;
                }
            }
        }

        if (isTypingVariable) {
            setFilteredVariables(
                variables.filter((variable) =>
                    variable.toLowerCase().includes(partialVariable.toLowerCase())
                )
            );

            // Вычисляем позицию дропдауна после обновления состояния
            setTimeout(() => {
                if (editorRef.current && !isClosingDropdown.current) {
                    const selectionRect = getVisibleSelectionRect(window);

                    // Проверяем, что selectionRect валиден и находится внутри editorRef
                    if (
                        selectionRect &&
                        editorRef.current
                    ) {
                        const editorRect = editorRef.current.getBoundingClientRect();
                        // Проверяем, что selectionRect действительно внутри редактора
                        const isInside =
                            selectionRect.left >= editorRect.left &&
                            selectionRect.right <= editorRect.right &&
                            selectionRect.top >= editorRect.top &&
                            selectionRect.bottom <= editorRect.bottom;

                        if (isInside) {
                            const top = selectionRect.bottom - editorRect.top;
                            const left = selectionRect.left - editorRect.left;

                            setDropdownPosition({ top, left });
                            setDropdownVisible(true);
                        } else {
                            setDropdownVisible(false);
                        }
                    } else {
                        setDropdownVisible(false);
                    }
                }
            }, 0);
        } else if (!hasClosedVariable) {
            // Если не печатаем переменную и не закрыли её только что
            setDropdownVisible(false);
        }
    };

    const insertVariable = (variable: string) => {
        const contentState = editorState.getCurrentContent();
        const selectionState = editorState.getSelection();
        const blockKey = selectionState.getStartKey();
        const block = contentState.getBlockForKey(blockKey);
        const text = block.getText();

        const cursorPosition = selectionState.getStartOffset();

        // Ищем, где начинается {{
        let variableStartPos = cursorPosition;

        for (let i = cursorPosition - 1; i >= 0; i--) {
            if (text.substring(i, i + 2) === '{{') {
                variableStartPos = i;
                break;
            }
        }

        // Ищем, где заканчивается переменная (закрывающие }})
        let variableEndPos = cursorPosition;
        const textAfterStart = text.substring(variableStartPos);
        const closingBracketsPos = textAfterStart.indexOf('}}');

        // Если нашли закрывающие скобки после открывающих, используем как конечную позицию
        if (closingBracketsPos !== -1) {
            variableEndPos = variableStartPos + closingBracketsPos + 2; // +2 для символов }}
        }

        // Создаем диапазон выделения от {{ до }} или от {{ до курсора, если не нашли закрывающие скобки
        const variableSelectionState = SelectionState.createEmpty(blockKey).merge({
            anchorOffset: variableStartPos,
            focusOffset: variableEndPos,
        });

        // Текст для вставки с синтаксисом переменной
        const variableText = `{{${variable}}}`;

        // Проверяем maxLength, если он задан
        if (maxLength !== undefined) {
            const currentLength = contentState.getPlainText().length;
            const variableLength = variableText.length;
            const selectionLength = variableEndPos - variableStartPos;
            const newTotalLength = currentLength - selectionLength + variableLength;

            if (newTotalLength > maxLength) {
                return; // Не вставляем, если превышает maxLength
            }
        }

        // Заменяем на полный синтаксис переменной
        const contentWithVariable = Modifier.replaceText(
            contentState,
            variableSelectionState,
            variableText
        );

        // Вычисляем позицию после вставленной переменной
        const endPosition = variableStartPos + variableText.length;

        // Создаем состояние выделения, которое помещает курсор в конец вставленной переменной
        const endSelectionState = SelectionState.createEmpty(blockKey).merge({
            anchorOffset: endPosition,
            focusOffset: endPosition,
        });

        // Создаем новое состояние редактора с вставленной переменной
        let newEditorState = EditorState.push(
            editorState,
            contentWithVariable,
            'insert-characters'
        );

        // Применяем состояние выделения для позиционирования курсора в конце
        newEditorState = EditorState.forceSelection(newEditorState, endSelectionState);

        // Обновляем состояние редактора
        setEditorState(newEditorState);

        // Обновляем реф текущего значения
        const newText = contentWithVariable.getPlainText();

        currentValueRef.current = newText;

        // Вызываем внешний обработчик onChange если он есть
        if (onChange) {
            onChange(newText);
        }

        setDropdownVisible(false);
    };

    // Обработка клавиш для навигации по дропдауну
    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (dropdownVisible) {
            if (e.key === 'ArrowUp') {
                e.preventDefault();
                setSelectedIndex((prev) => (prev > 0 ? prev - 1 : filteredVariables.length - 1));
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                setSelectedIndex((prev) => (prev < filteredVariables.length - 1 ? prev + 1 : 0));
            } else if (e.key === 'Enter' && filteredVariables.length > 0) {
                e.preventDefault();
                insertVariable(filteredVariables[selectedIndex]);
            } else if (e.key === 'Escape') {
                e.preventDefault();
                setDropdownVisible(false);
            }
        }
    };

    // Обработчики фокуса для совместимости с Form.Item
    const handleBlur = (e: React.FocusEvent<any>) => {
        setIsFocused(false);
        setDropdownVisible(false); // Закрываем дропдаун при потере фокуса
        if (onBlur) {
            onBlur(e);
        }
    };

    const handleFocus = (e: React.FocusEvent<any>) => {
        setIsFocused(true);
        if (onFocus) {
            onFocus(e);
        }
    };

    const handleMouseEnter = () => {
        if (!disabled) {
            setIsHovered(true);
        }
    };

    const handleMouseLeave = () => {
        setIsHovered(false);
    };

    // Функция для очистки поля ввода
    const handleClear = (e: React.MouseEvent) => {
        e.stopPropagation();
        updateEditorContent('');
        if (onChange) {
            onChange('');
        }
        // Фокус на редактор после очистки
        setTimeout(() => {
            internalEditorRef.current?.focus();
        }, 0);
    };

    // Рассчитываем минимальную высоту в зависимости от autoSize
    const getMinHeight = () => {
        if (!autoSize) return undefined;

        if (typeof autoSize === 'object' && autoSize.minRows) {
            return `${autoSize.minRows * 22}px`; // примерно 22px на строку
        }

        return undefined;
    };

    // Рассчитываем максимальную высоту в зависимости от autoSize
    const getMaxHeight = () => {
        if (!autoSize) return;
        if (typeof autoSize === 'object' && autoSize.maxRows) {
            return `${autoSize.maxRows * 22}px`; // примерно 22px на строку
        }

        return undefined;
    };

    // Определяем классы для разных состояний компонента
    const getContainerClassNames = () => {
        const classNames = [styles.highlightTextarea, CLASSNAMES.textareaWithVariables];

        if (className) {
            classNames.push(className);
        }

        if (status === 'error') {
            classNames.push(styles.error);
        } else if (status === 'warning') {
            classNames.push(styles.warning);
        }

        if (disabled) {
            classNames.push(styles.disabled);
        }

        if (isFocused) {
            classNames.push(styles.focused);
        }

        if (isHovered && !disabled && !isFocused) {
            classNames.push(styles.hovered);
        }

        if (!bordered) {
            classNames.push(styles.borderless);
        }

        if (disableLineBreak) {
            classNames.push(styles.singleLine);
        }

        return classNames.join(' ');
    };

    // Загрузка переменных с использованием предоставленной функции
    useEffect(() => {
        if (initialVariables) {
            setVariables(initialVariables);
            variablesLoaded.current = true;
        }
    }, [initialVariables]);

    useEffect(() => {
        if (!isFocused) {
            setDropdownVisible(false)
        }
    }, [isFocused]);

    // Создаем элементы меню для Ant Design Dropdown
    const menu = {
        items: filteredVariables.map((variable, index) => ({
            key: variable,
            label: (
                <div
                    onClick={ () => insertVariable(variable) }
                    onMouseDown={ (e) => {
                        // Предотвращаем потерю фокуса редактора и преждевременное закрытие дропдауна
                        e.preventDefault();
                        e.stopPropagation();
                    } }
                    style={ { whiteSpace: 'nowrap', padding: `5px 12px` } }
                >
                    {variable}
                </div>
            ),
            className: cn(styles.dropdownItemWrapper, { [styles.selectedItem]: index === selectedIndex })
        }))
    }

    // Настройки для Dropdown
    const dropdownProps: DropdownProps = {
        menu: { ...menu, className: styles.dropdownMenu },
        trigger: ['click'],
        open: dropdownVisible && filteredVariables.length > 0,
        placement: 'bottomLeft',
        getPopupContainer: () => (renderInBody ? document.body : editorRef.current || document.body),
        destroyPopupOnHide: true,
        onOpenChange: (visible) => {
            if (!visible) {
                setDropdownVisible(false);
            }
        }
    };

    return (
        <div
            ref={ wrapperRef }
            className={ styles.textareaWrapper }
            style={ {
                width: '100%',
                ...style
            } }
        >
            <div
                ref={ editorRef }
                className={ getContainerClassNames() }
                data-editor-id={ id }
                onClick={ onClick }
                onKeyDown={ handleKeyDown }
                onMouseEnter={ handleMouseEnter }
                onMouseLeave={ handleMouseLeave }
                style={ {
                    cursor: 'text',
                    minHeight: getMinHeight(),
                    maxHeight: getMaxHeight(),
                    resize: autoSize ? 'none' : 'vertical',
                } }
            >
                <Editor
                    ref={ internalEditorRef }
                    editorState={ editorState }
                    onBlur={ handleBlur }
                    onChange={ handleChange }
                    onFocus={ handleFocus }
                    placeholder={ placeholder }
                    readOnly={ disabled }
                />

                {allowClear && !disabled && currentValueRef.current && (
                    <span
                        className={ styles.clearBtn }
                        onClick={ handleClear }
                    >
                        ×
                    </span>
                )}
            </div>

            {/* Используем Ant Design Dropdown вместо кастомного */}
            {!disableAutoComplete && <Dropdown { ...dropdownProps }>
                <div
                    style={ {
                        position: 'absolute',
                        top: `${dropdownPosition.top}px`,
                        left: `${dropdownPosition.left}px`,
                        visibility: 'hidden',
                        height: 0,
                        background: 'transparent'
                    } }></div>
            </Dropdown>}
        </div>
    );
});
