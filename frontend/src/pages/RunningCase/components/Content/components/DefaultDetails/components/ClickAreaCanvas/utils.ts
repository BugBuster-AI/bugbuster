/**
 * Интерфейс для координат прямоугольника
 */
export interface Rectangle {
    x: number;
    y: number;
    width: number;
    height: number;
}

/**
 * Интерфейс для координат в пикселях относительно оригинального изображения
 */
export interface RelativeCoordinates {
    x: number; // пиксели от левого края изображения
    y: number; // пиксели от верхнего края изображения
    width: number; // ширина в пикселях
    height: number; // высота в пикселях
}

/**
 * Загружает изображение и возвращает Promise с HTMLImageElement
 */
export const loadImage = (src: string): Promise<HTMLImageElement> => {
    return new Promise((resolve, reject) => {
        const img = new Image();

        img.crossOrigin = 'anonymous';
        img.onload = () => resolve(img);
        img.onerror = reject;
        img.src = src;
    });
};

/**
 * Рисует изображение на canvas с подгонкой под размеры canvas
 */
export const drawImageOnCanvas = (
    ctx: CanvasRenderingContext2D,
    img: HTMLImageElement,
    canvasWidth: number,
    canvasHeight: number
): { offsetX: number; offsetY: number; scale: number } => {
    const imgAspect = img.width / img.height;
    const canvasAspect = canvasWidth / canvasHeight;

    let drawWidth = canvasWidth;
    let drawHeight = canvasHeight;
    let offsetX = 0;
    let offsetY = 0;

    // Подгоняем изображение под canvas с сохранением пропорций
    if (imgAspect > canvasAspect) {
        drawHeight = canvasWidth / imgAspect;
        offsetY = (canvasHeight - drawHeight) / 2;
    } else {
        drawWidth = canvasHeight * imgAspect;
        offsetX = (canvasWidth - drawWidth) / 2;
    }

    ctx.clearRect(0, 0, canvasWidth, canvasHeight);
    ctx.drawImage(img, offsetX, offsetY, drawWidth, drawHeight);

    return {
        offsetX,
        offsetY,
        scale: drawWidth / img.width,
    };
};

/**
 * Рисует прямоугольник выделения
 */
export const drawRectangle = (
    ctx: CanvasRenderingContext2D,
    rect: Rectangle,
    color: string,
    isDragging: boolean = false
) => {
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.setLineDash(isDragging ? [5, 5] : []);
    ctx.strokeRect(rect.x, rect.y, rect.width, rect.height);

    // Полупрозрачная заливка
    ctx.fillStyle = `${color}20`;
    ctx.fillRect(rect.x, rect.y, rect.width, rect.height);

    ctx.setLineDash([]);
};

/**
 * Конвертирует абсолютные координаты canvas в координаты пикселей относительно оригинального изображения
 */
export const convertToRelativeCoordinates = (
    rect: Rectangle,
    imageWidth: number,
    imageHeight: number,
    offsetX: number,
    offsetY: number,
    scale: number
): RelativeCoordinates => {
    // Вычитаем offset и делим на scale для получения координат относительно оригинального изображения
    const imgX = (rect.x - offsetX) / scale;
    const imgY = (rect.y - offsetY) / scale;
    const imgWidth = rect.width / scale;
    const imgHeight = rect.height / scale;

    // Ограничиваем координаты границами изображения и округляем до целых пикселей
    const clampedX = Math.max(0, Math.min(imgX, imageWidth));
    const clampedY = Math.max(0, Math.min(imgY, imageHeight));
    const clampedWidth = Math.min(imgWidth, imageWidth - clampedX);
    const clampedHeight = Math.min(imgHeight, imageHeight - clampedY);

    // Возвращаем координаты в пикселях относительно оригинального изображения
    return {
        x: Math.round(clampedX),
        y: Math.round(clampedY),
        width: Math.round(clampedWidth),
        height: Math.round(clampedHeight),
    };
};

/**
 * Нормализует прямоугольник (на случай если рисовали справа налево или снизу вверх)
 */
export const normalizeRectangle = (rect: Rectangle): Rectangle => {
    return {
        x: rect.width < 0 ? rect.x + rect.width : rect.x,
        y: rect.height < 0 ? rect.y + rect.height : rect.y,
        width: Math.abs(rect.width),
        height: Math.abs(rect.height),
    };
};

/**
 * Проверяет, находится ли точка внутри прямоугольника с учетом offset
 */
export const isPointInDrawableArea = (
    x: number,
    y: number,
    offsetX: number,
    offsetY: number,
    drawWidth: number,
    drawHeight: number
): boolean => {
    return (
        x >= offsetX &&
        x <= offsetX + drawWidth &&
        y >= offsetY &&
        y <= offsetY + drawHeight
    );
};
