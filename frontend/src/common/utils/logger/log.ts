export class Logger {
    static log (...args: any[]) {
        if (import.meta.env.DEV) {
            console.log(...args);
        }
    }

    static error (...args: any[]) {
        console.error(...args);
    }
}
