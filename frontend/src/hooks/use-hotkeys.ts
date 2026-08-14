import { useEffect, useRef } from 'react'

export function useHotkeys(
  keys: string[],
  handler: (e: KeyboardEvent) => void,
  deps: unknown[] = [],
) {
  const handlerRef = useRef(handler)
  handlerRef.current = handler

  useEffect(() => {
    const listener = (e: KeyboardEvent) => {
      const isMac = navigator.platform.toUpperCase().includes('MAC')
      const mod = isMac ? e.metaKey : e.ctrlKey
      for (const key of keys) {
        const normalized = key.toLowerCase()
        if (normalized.includes('ctrl') || normalized.includes('meta')) {
          const rest = normalized.replace('ctrl+', '').replace('meta+', '').trim()
          if (mod && e.key.toLowerCase() === rest) {
            handlerRef.current(e)
            return
          }
        } else if (e.key.toLowerCase() === normalized) {
          handlerRef.current(e)
          return
        }
      }
    }
    window.addEventListener('keydown', listener)
    return () => window.removeEventListener('keydown', listener)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, keys.concat(deps as string[]))
}
