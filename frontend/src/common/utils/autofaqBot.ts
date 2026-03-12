export const openAutofaqBot = () => {
    try {
        //@ts-ignore
        autofaq.open()
    } catch {
        console.error(`[AUTOFAQ BOT]: open bot error`)
    }
}


export const sendUserFaqMessage = (message: string, openBot: boolean = true) => {
    try {
        //@ts-ignore
        window.autofaq.sendMessage({ text: message })
        if (openBot) {
            setTimeout(() => openAutofaqBot(), 100)
        }

    } catch {
        console.error(`[AUTOFAQ BOT]: send message error`)
    }
}
