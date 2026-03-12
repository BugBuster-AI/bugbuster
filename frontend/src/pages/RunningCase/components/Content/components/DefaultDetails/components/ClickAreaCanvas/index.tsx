import { useRunningStore } from '@Pages/RunningCase/store';
import { message, Spin } from 'antd';
import cn from 'classnames';
import { useCallback, useEffect, useRef, useState } from 'react';
import styles from './ClickAreaCanvas.module.scss';
import {
    convertToRelativeCoordinates,
    drawImageOnCanvas,
    drawRectangle,
    isPointInDrawableArea,
    loadImage,
    normalizeRectangle,
    Rectangle,
    RelativeCoordinates,
} from './utils';

interface ClickAreaCanvasProps {
    imageUrl: string;
    disableDraw?: boolean
}

export const ClickAreaCanvas = ({
    imageUrl,
    disableDraw
}: ClickAreaCanvasProps) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isDragging, setIsDragging] = useState(false);
    const [startPoint, setStartPoint] = useState<{ x: number; y: number } | null>(null);
    const [currentRect, setCurrentRect] = useState<Rectangle | null>(null);
    const [imageData, setImageData] = useState<{
        img: HTMLImageElement;
        offsetX: number;
        offsetY: number;
        scale: number;
        drawWidth: number;
        drawHeight: number;
    } | null>(null);

    const selectedEditingStep = useRunningStore((state) => state.selectedEditingStep)
    const updateEditingStep = useRunningStore((state) => state.updateEditingStep)
    const selectedStepEditData = selectedEditingStep?.step?.editingClickArea
    const selectedStepContextData = selectedEditingStep?.step?.contextScreenshotMode

    const highlightColor = selectedStepEditData?.highlightColor ?? selectedStepContextData?.highlightColor ?? '#1890ff'

    const coordinates = selectedStepEditData?.coordinates
             ?? selectedStepContextData?.coordinates
            

    const onAreaSelected = (coordinates: RelativeCoordinates) => {
        if (!selectedEditingStep) return;

        updateEditingStep(selectedEditingStep.id, {
            editingClickArea: {
                coordinates,
            }
        });
    };

    const onValidateError = () => {
        if (!selectedEditingStep) return;

        updateEditingStep(selectedEditingStep.id, {
            editingClickArea: {
                coordinates: undefined,
            }
        });
    }
    

    /**
     * Инициализация canvas и загрузка изображения
     */
    useEffect(() => {
        const initCanvas = async () => {
            if (!canvasRef.current) return;

            setIsLoading(true);
            try {
                const img = await loadImage(imageUrl);
                const canvas = canvasRef.current;
                const ctx = canvas.getContext('2d');

                if (!ctx) return;

                // Устанавливаем размеры canvas равными оригинальному изображению
                canvas.width = img.width;
                canvas.height = img.height;

                const { offsetX, offsetY, scale } = drawImageOnCanvas(
                    ctx,
                    img,
                    canvas.width,
                    canvas.height
                );

                const drawWidth = img.width * scale;
                const drawHeight = img.height * scale;

                setImageData({
                    img,
                    offsetX,
                    offsetY,
                    scale,
                    drawWidth,
                    drawHeight,
                });

                setIsLoading(false);
            } catch (error) {
                console.error('Failed to load image:', error);
                setIsLoading(false);
            }
        };

        initCanvas();
    }, [imageUrl]);

    useEffect(() => {
        if (coordinates  && imageData) {            
            setCurrentRect({
                x: coordinates.x,
                y: coordinates.y,
                width: coordinates.width,
                height: coordinates.height,
            });

            return;
        }
    }, [coordinates, imageData])

    /**
     * Очистка выделения при изменении coordinates извне
     */
    useEffect(() => {
        if (coordinates === undefined) {
            setCurrentRect(null);
            setStartPoint(null);
        }
    }, [coordinates]);

    /**
     * Перерисовка canvas при изменении выделения или изображения
     */
    useEffect(() => {
        if (!canvasRef.current || !imageData) return;

        const ctx = canvasRef.current.getContext('2d');

        if (!ctx) return;

        // Перерисовываем изображение
        drawImageOnCanvas(ctx, imageData.img, canvasRef.current.width, canvasRef.current.height);

        // Рисуем текущее выделение
        if (currentRect) {
            drawRectangle(ctx, currentRect, highlightColor, isDragging);
        }
    }, [currentRect, imageData, highlightColor, isDragging]);

    /**
     * Получение координат мыши относительно canvas
     */
    const getMousePosition = useCallback(
        (event: React.MouseEvent<HTMLCanvasElement>): { x: number; y: number } => {
            if (!canvasRef.current) return { x: 0, y: 0 };

            const rect = canvasRef.current.getBoundingClientRect();
            const scaleX = canvasRef.current.width / rect.width;
            const scaleY = canvasRef.current.height / rect.height;

            return {
                x: (event.clientX - rect.left) * scaleX,
                y: (event.clientY - rect.top) * scaleY,
            };
        },
        []
    );

    /**
     * Начало выделения области
     */
    const handleMouseDown = useCallback(
        (event: React.MouseEvent<HTMLCanvasElement>) => {
            if (disableDraw) return

            if (!imageData) return;

            const pos = getMousePosition(event);

            // Проверяем, что клик внутри области изображения
            if (
                !isPointInDrawableArea(
                    pos.x,
                    pos.y,
                    imageData.offsetX,
                    imageData.offsetY,
                    imageData.drawWidth,
                    imageData.drawHeight
                )
            ) {
                return;
            }

            setIsDragging(true);
            setStartPoint(pos);
            setCurrentRect({
                x: pos.x,
                y: pos.y,
                width: 0,
                height: 0,
            });
        },
        [imageData, getMousePosition]
    );

    /**
     * Процесс выделения области
     */
    const handleMouseMove = useCallback(
        (event: React.MouseEvent<HTMLCanvasElement>) => {
            if (disableDraw) return
            if (!isDragging || !startPoint || !imageData) return;

            const pos = getMousePosition(event);

            // Ограничиваем координаты областью изображения
            const clampedX = Math.max(
                imageData.offsetX,
                Math.min(pos.x, imageData.offsetX + imageData.drawWidth)
            );
            const clampedY = Math.max(
                imageData.offsetY,
                Math.min(pos.y, imageData.offsetY + imageData.drawHeight)
            );

            setCurrentRect({
                x: startPoint.x,
                y: startPoint.y,
                width: clampedX - startPoint.x,
                height: clampedY - startPoint.y,
            });
        },
        [isDragging, startPoint, imageData, getMousePosition]
    );

    /**
     * Завершение выделения области
     */
    const handleMouseUp = useCallback(() => {
        if (disableDraw) return
        if (!isDragging || !currentRect || !imageData) return;

        setIsDragging(false);

        const normalized = normalizeRectangle(currentRect);

        // Игнорируем слишком маленькие выделения (случайные клики)
        if (normalized.width < 10 || normalized.height < 10) {
            const messageText = 'Selected area is too small. Please select a larger area.';

            message.warning(messageText);
            setCurrentRect(null);
            setStartPoint(null);
            onValidateError();

            return;
        }

        // Конвертируем в относительные координаты
        const relativeCoords = convertToRelativeCoordinates(
            normalized,
            imageData.img.width,
            imageData.img.height,
            imageData.offsetX,
            imageData.offsetY,
            imageData.scale
        );

        // Вызываем callback с координатами
        onAreaSelected?.(relativeCoords);

        setCurrentRect(normalized);
        setStartPoint(null);
    }, [isDragging, currentRect, imageData, onAreaSelected]);

    /**
     * Отмена выделения при выходе за пределы canvas
     */
    const handleMouseLeave = useCallback(() => {
        if (disableDraw) return

        if (isDragging) {
            handleMouseUp();
        }
    }, [isDragging, handleMouseUp]);

    /**
     * Очистка текущего выделения
     */
    const clearSelection = useCallback(() => {
        setCurrentRect(null);
        setStartPoint(null);
    }, []);

    // метод для очистки 
    useEffect(() => {
        if (canvasRef.current) {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (canvasRef.current as any).clearSelection = clearSelection;
        }
    }, [clearSelection]);
    
    return (
        <div className={ styles.canvasWrapper }>

            {isLoading && <div className={ styles.loader }><Spin spinning /></div>}
            
            <canvas
                ref={ canvasRef }
                className={ cn({ 
                    [styles.dragging]: isDragging,
                    [styles.loading]: isLoading, 
                    [styles.disable]: disableDraw
                }) }
                onMouseDown={ handleMouseDown }
                onMouseLeave={ handleMouseLeave }
                onMouseMove={ handleMouseMove }
                onMouseUp={ handleMouseUp }
            />
        </div>
    );
};
