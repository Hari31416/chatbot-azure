import {
  PublicClientApplication,
  type AuthenticationResult,
} from '@azure/msal-browser'

const msalConfig = {
  auth: {
    clientId: import.meta.env.VITE_AZURE_CLIENT_ID || '',
    authority: import.meta.env.VITE_ENTRA_AUTHORITY || '',
    redirectUri: window.location.origin,
  },
  cache: {
    cacheLocation: 'localStorage' as const,
    storeAuthStateInCookie: false,
  },
}

const loginRequest = {
  scopes: ['openid', 'profile', 'email'],
}

let msalInstance: PublicClientApplication | null = null
let msalInitPromise: Promise<PublicClientApplication> | null = null

export async function getMsalInstance(): Promise<PublicClientApplication> {
  if (msalInitPromise) return msalInitPromise

  const instance = new PublicClientApplication(msalConfig)
  msalInstance = instance
  msalInitPromise = instance.initialize().then(() => instance)
  return msalInitPromise
}

export interface AuthSession {
  accessToken: string
  idToken: string
  email: string
}

export async function signUpUser(
  email: string,
  _password: string,
): Promise<string> {
  const instance = await getMsalInstance()
  await instance.loginPopup({
    ...loginRequest,
    authority: `${msalConfig.auth.authority}/signup`,
    loginHint: email,
  })
  return email
}

export async function confirmSignUpUser(
  _email: string,
  _code: string,
): Promise<boolean> {
  return true
}

export async function signInUser(
  email: string,
  _password: string,
): Promise<AuthSession> {
  const instance = await getMsalInstance()
  const result: AuthenticationResult = await instance.loginPopup({
    ...loginRequest,
    loginHint: email,
  })

  const session: AuthSession = {
    accessToken: result.accessToken,
    idToken: result.idToken || '',
    email: result.account?.username || email,
  }

  localStorage.setItem('auth_id_token', session.idToken)
  localStorage.setItem('auth_access_token', session.accessToken)
  localStorage.setItem('auth_user_email', session.email)

  return session
}

export function signOutUser(): void {
  if (msalInstance) {
    msalInstance.logoutPopup().catch((err) => {
      console.error('Logout error:', err)
    })
  }
  localStorage.removeItem('auth_id_token')
  localStorage.removeItem('auth_access_token')
  localStorage.removeItem('auth_user_email')
}

export function isUserLoggedIn(): boolean {
  if (!msalInstance) return !!localStorage.getItem('auth_id_token')
  const accounts = msalInstance.getAllAccounts()
  return accounts.length > 0
}

export function getCurrentUserEmail(): string {
  if (msalInstance) {
    const accounts = msalInstance.getAllAccounts()
    if (accounts.length > 0) return accounts[0].username
  }
  return localStorage.getItem('auth_user_email') || 'Guest'
}

export async function getCurrentSessionToken(): Promise<string | null> {
  if (!msalInstance) {
    const localToken = localStorage.getItem('auth_id_token')
    if (!localToken) return null
    try {
      await getMsalInstance()
    } catch {
      return localToken
    }
  }

  const accounts = msalInstance!.getAllAccounts()
  if (accounts.length === 0) return localStorage.getItem('auth_id_token')

  try {
    const result = await msalInstance!.acquireTokenSilent({
      ...loginRequest,
      account: accounts[0],
    })
    const finalToken = result.idToken || result.accessToken
    if (finalToken) {
      localStorage.setItem('auth_id_token', result.idToken || '')
      localStorage.setItem('auth_access_token', result.accessToken)
    }
    return finalToken
  } catch {
    return localStorage.getItem('auth_id_token')
  }
}
