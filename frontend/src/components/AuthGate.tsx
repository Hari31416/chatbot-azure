import * as React from 'react'
import { SignIn, SignUp } from '@clerk/react'

type ClerkAuthPath = 'sign-in' | 'sign-up'

function readAuthPathFromHash(): ClerkAuthPath {
  const hash = window.location.hash.toLowerCase()
  if (hash.includes('sign-up') || hash.includes('signup')) {
    return 'sign-up'
  }
  return 'sign-in'
}

function useClerkAuthPath(): ClerkAuthPath {
  const [path, setPath] = React.useState<ClerkAuthPath>(readAuthPathFromHash)

  React.useEffect(() => {
    const sync = () => setPath(readAuthPathFromHash())
    window.addEventListener('hashchange', sync)
    return () => window.removeEventListener('hashchange', sync)
  }, [])

  return path
}

export function AuthGate() {
  const authPath = useClerkAuthPath()
  const isSignUp = authPath === 'sign-up'

  return (
    <div className="flex h-screen w-screen items-center justify-center bg-zinc-50 font-sans text-zinc-800 dark:bg-zinc-950 dark:text-zinc-100">
      <div className="w-full max-w-md px-4">
        <div className="text-center space-y-1 mb-6">
          <h1 className="text-lg font-bold tracking-tight text-blue-600 dark:text-blue-500">
            Chatbot
          </h1>
          <p className="text-xs text-zinc-400">
            {isSignUp
              ? 'Create an account to get started'
              : 'Sign in to access your chatbot'}
          </p>
        </div>

        {isSignUp ? (
          <SignUp
            routing="hash"
            signInUrl="#/sign-in"
            fallbackRedirectUrl="/"
            forceRedirectUrl="/"
          />
        ) : (
          <SignIn
            routing="hash"
            signUpUrl="#/sign-up"
            fallbackRedirectUrl="/"
            forceRedirectUrl="/"
          />
        )}
      </div>
    </div>
  )
}
