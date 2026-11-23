/**
 * 多 Tab 同步 access（仅内存广播，不落盘）与 refresh 单飞协调。
 */
export type AuthSyncMessage =
  | { type: 'access'; accessToken: string | null }
  | { type: 'logout' }
  | { type: 'refresh-start' }
  | { type: 'refresh-done'; accessToken: string | null }

const CHANNEL = 'dbc-auth'

type Listener = (msg: AuthSyncMessage) => void

let channel: BroadcastChannel | null = null
const listeners = new Set<Listener>()

function ensureChannel(): BroadcastChannel | null {
  if (typeof BroadcastChannel === 'undefined') return null
  if (!channel) {
    channel = new BroadcastChannel(CHANNEL)
    channel.onmessage = (ev: MessageEvent<AuthSyncMessage>) => {
      const data = ev.data
      if (!data || typeof data !== 'object') return
      listeners.forEach((fn) => fn(data))
    }
  }
  return channel
}

export function subscribeAuthSync(listener: Listener): () => void {
  ensureChannel()
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function publishAuthSync(msg: AuthSyncMessage) {
  ensureChannel()?.postMessage(msg)
}
