/** 可读 Cookie 辅助（csrf）；禁止用于存放 accessToken。 */

const CSRF_COOKIE = 'dbc_csrf'

export function readCookie(name: string): string | null {
  if (typeof document === 'undefined') return null
  const escaped = name.replace(/([.$?*|{}()[\]\\/+^])/g, '\\$1')
  const match = document.cookie.match(new RegExp(`(?:^|; )${escaped}=([^;]*)`))
  return match ? decodeURIComponent(match[1]) : null
}

export function readCsrfCookie(): string | null {
  return readCookie(CSRF_COOKIE)
}
