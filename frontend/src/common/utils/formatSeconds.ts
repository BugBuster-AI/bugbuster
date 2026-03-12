export const formatSeconds = (seconds: number, t: (v: string) => string) => {
    const tr = {
        sec: t('common.sec'),
        min: t('common.min'),
        h: t('common.h')
    }

    if (seconds < 60) {
        return `${seconds.toFixed(2)} ${tr.sec}`;
    } else if (seconds < 3600) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.floor(seconds) % 60;

        return `${minutes}${tr.min} ${remainingSeconds.toString().padStart(2, '0')}${tr.sec}`;
    } else {
        const hours = Math.floor(seconds / 3600);
        const remainingMinutes = Math.floor((seconds % 3600) / 60);

        return `${hours}${tr.h} ${remainingMinutes.toString().padStart(2, '0')}${tr.min}`;
    }
}
