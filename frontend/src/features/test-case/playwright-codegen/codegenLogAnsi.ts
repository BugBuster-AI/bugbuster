import Anser, { type AnserJsonEntry } from 'anser'
import { type CSSProperties, createElement, type ReactNode } from 'react'

/**
 * Restore ESC bytes lost during UTF-8 decode (shows up as U+FFFD before `[`).
 * Also strip orphan CSI-like fragments that have no preceding ESC at all
 * — only when preceded by U+FFFD or at the very start of the string
 * (avoids false positives on code like `array[0m]`).
 */
function normalizeAnsi (raw: string): string {
    let s = raw.replace(/\uFFFD\[/g, '\x1B[')
    s = s.replace(/(^|(?<=\uFFFD))\[([0-9;]*m)/g, '\x1B[$2')
    return s
}

const ANSI_RE = /\x1B\[[0-?]*[ -/]*[@-~]/g

export function stripAnsi (text: string): string {
    return normalizeAnsi(text).replace(ANSI_RE, '').replace(/\uFFFD/g, '')
}

const ANSER_COLORS: Record<string, string> = {
    'ansi-black': '#1e1e1e',
    'ansi-red': '#cd3131',
    'ansi-green': '#0dbc79',
    'ansi-yellow': '#e5e510',
    'ansi-blue': '#2472c8',
    'ansi-magenta': '#bc3fbc',
    'ansi-cyan': '#11a8cd',
    'ansi-white': '#e5e5e5',
    'ansi-bright-black': '#666666',
    'ansi-bright-red': '#f14c4c',
    'ansi-bright-green': '#23d18b',
    'ansi-bright-yellow': '#f5f543',
    'ansi-bright-blue': '#3b8eea',
    'ansi-bright-magenta': '#d670d6',
    'ansi-bright-cyan': '#29b8db',
    'ansi-bright-white': '#ffffff',
}

function anserStyle (entry: AnserJsonEntry): CSSProperties | undefined {
    const style: CSSProperties = {}
    let has = false
    if (entry.fg) {
        style.color = ANSER_COLORS[entry.fg] ?? undefined
        if (style.color) has = true
    }
    if (entry.bg) {
        style.backgroundColor = ANSER_COLORS[entry.bg] ?? undefined
        if (style.backgroundColor) has = true
    }
    if (entry.decorations?.includes('bold')) {
        style.fontWeight = 700
        has = true
    }
    if (entry.decorations?.includes('dim')) {
        style.opacity = 0.6
        has = true
    }
    if (entry.decorations?.includes('italic')) {
        style.fontStyle = 'italic'
        has = true
    }
    return has ? style : undefined
}

export function ansiToReactNodes (raw: string): ReactNode[] {
    const normalized = normalizeAnsi(raw)
    const entries = Anser.ansiToJson(normalized, { use_classes: true })
    return entries.map((entry, i) => {
        const style = anserStyle(entry)
        if (!style) return entry.content
        return createElement('span', { key: i, style }, entry.content)
    })
}
