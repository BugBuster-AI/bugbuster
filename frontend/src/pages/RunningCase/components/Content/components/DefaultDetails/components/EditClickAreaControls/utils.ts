/**
 * Загружает изображение по URL и преобразует его в base64 строку
 * @param imageUrl - URL изображения
 * @returns Promise с base64 строкой без префикса data:image/...
 */
export const convertImageToBase64 = async (imageUrl: string): Promise<string> => {
    return new Promise((resolve, reject) => {
        const img = new Image();

        img.crossOrigin = 'anonymous';
        
        img.onload = () => {
            try {
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                
                if (!ctx) {
                    reject(new Error('Failed to get canvas context'));

                    return;
                }

                canvas.width = img.width;
                canvas.height = img.height;
                
                ctx.drawImage(img, 0, 0);
                
                // Получаем base64 строку
                const dataURL = canvas.toDataURL('image/png');
                
                // Удаляем префикс "data:image/png;base64,"
                const base64 = dataURL.split(',')[1];
                
                resolve(base64);
            } catch (error) {
                reject(error);
            }
        };
        
        img.onerror = () => {
            reject(new Error('Failed to load image'));
        };
        
        img.src = imageUrl;
    });
};
