import { RotateCwIcon } from 'lucide-react'

import { Alert, AlertAction, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'

interface LoadErrorProps {
  title: string
  error: Error
  onRetry: () => void
  retrying: boolean
}

/** A failed page or list load, with a Retry button. */
export function LoadError({ title, error, onRetry, retrying }: LoadErrorProps) {
  return (
    <Alert variant="destructive">
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>{error.message}</AlertDescription>
      <AlertAction>
        <Button variant="outline" size="sm" disabled={retrying} onClick={onRetry}>
          <RotateCwIcon className={retrying ? 'animate-spin' : ''} />
          Retry
        </Button>
      </AlertAction>
    </Alert>
  )
}
