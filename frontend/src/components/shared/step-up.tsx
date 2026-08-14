import { useState } from 'react'
import { ShieldAlert } from 'lucide-react'
import { useAuth } from '@/stores/auth'
import { api, showError } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'

export interface StepUpHandle {
  open: boolean
  needsTotp: boolean
  submitting: boolean
  confirm: (action: (token: string) => Promise<unknown>) => void
  execute: (password: string, totpCode: string) => Promise<unknown>
  close: () => void
}

export function useStepUp(): StepUpHandle {
  const user = useAuth((s) => s.user)
  const [open, setOpen] = useState(false)
  const [pending, setPending] = useState<((token: string) => Promise<unknown>) | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const close = () => {
    setOpen(false)
    setPending(null)
  }

  const confirm = (action: (token: string) => Promise<unknown>) => {
    setPending(() => action)
    setOpen(true)
  }

  const execute = async (password: string, totpCode: string) => {
    if (!pending) return
    setSubmitting(true)
    let token: string
    try {
      const body: Record<string, string> = { password }
      if (user?.twofa_enabled) body.totp_code = totpCode
      const res = await api.post<{ step_up_token: string }>('/auth/step-up', body)
      token = res.step_up_token
    } catch (err) {
      showError(err, 'Verification failed')
      throw err
    } finally {
      setSubmitting(false)
    }
    await pending(token)
    close()
  }

  return {
    open,
    needsTotp: !!user?.twofa_enabled,
    submitting,
    confirm,
    execute,
    close,
  }
}

export function StepUpDialog({ handle }: { handle: StepUpHandle }) {
  const [password, setPassword] = useState('')
  const [totp, setTotp] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const run = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    try {
      await handle.execute(password, totp)
      setPassword('')
      setTotp('')
    } catch {
      /* error already surfaced by execute */
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={handle.open} onOpenChange={(o) => !o && handle.close()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Confirm sensitive action</DialogTitle>
          <DialogDescription>
            For your security, re-enter your password{handle.needsTotp ? ' and 6-digit authenticator code' : ''} to
            continue.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={run} className="space-y-4">
          <div className="flex items-start gap-3 rounded-lg border border-amber-400/25 bg-amber-400/5 p-3 text-xs text-amber-300">
            <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
            <span>This action changes account roles, CVX balances, secrets, or server infrastructure.</span>
          </div>
          <div className="space-y-2">
            <Label htmlFor="stepup-password">Password</Label>
            <Input
              id="stepup-password"
              type="password"
              autoFocus
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Current password"
            />
          </div>
          {handle.needsTotp && (
            <div className="space-y-2">
              <Label htmlFor="stepup-totp">Authenticator code</Label>
              <Input
                id="stepup-totp"
                inputMode="numeric"
                maxLength={6}
                value={totp}
                onChange={(e) => setTotp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                placeholder="000000"
                className="font-mono tracking-widest"
              />
            </div>
          )}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={handle.close}>
              Cancel
            </Button>
            <Button type="submit" loading={submitting || handle.submitting} disabled={!password}>
              Confirm
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
