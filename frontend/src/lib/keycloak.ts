import Keycloak from 'keycloak-js'

const keycloak = new Keycloak({
  url: import.meta.env.VITE_KEYCLOAK_URL || 'http://localhost:8080',
  realm: 'knowledge',
  clientId: 'knowledge-web',
})

export default keycloak

let refreshInterval: ReturnType<typeof setInterval> | null = null

export async function initKeycloak(): Promise<boolean> {
  const authenticated = await keycloak.init({
    onLoad: 'login-required',
    checkLoginIframe: false,
    pkceMethod: 'S256',
  })

  if (authenticated && !refreshInterval) {
    refreshInterval = setInterval(async () => {
      try {
        await keycloak.updateToken(30)
      } catch {
        keycloak.login()
      }
    }, 10_000)
  }

  return authenticated
}

export function getToken(): string {
  return keycloak.token ?? ''
}

export function getUserDisplayName(): string {
  const parsed = keycloak.tokenParsed
  if (!parsed) return 'User'
  return (
    (parsed as Record<string, unknown>)['preferred_username'] as string ??
    (parsed as Record<string, unknown>)['name'] as string ??
    (parsed as Record<string, unknown>)['email'] as string ??
    'User'
  )
}

export function logout(): void {
  if (refreshInterval) {
    clearInterval(refreshInterval)
    refreshInterval = null
  }
  keycloak.logout({ redirectUri: window.location.origin })
}
