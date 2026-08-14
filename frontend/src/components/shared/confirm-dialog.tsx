import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { AlertTriangle } from 'lucide-react'
import { useState } from 'react'

interface ConfirmDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description?: React.ReactNode
  confirmText?: string
  danger?: boolean
  requireType?: string
  loading?: boolean
  onConfirm: () => void
}

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmText = 'Confirm',
  danger = false,
  requireType,
  loading,
  onConfirm,
}: ConfirmDialogProps) {
  const [typed, setTyped] = useState('')
  const needsType = Boolean(requireType)
  const canConfirm = !needsType || typed === requireType

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {danger && <AlertTriangle className="h-5 w-5 text-destructive" />}
            {title}
          </DialogTitle>
          {description && <DialogDescription asChild><div>{description}</div></DialogDescription>}
        </DialogHeader>
        {needsType && (
          <div className="space-y-2">
            <Label>Type <span className="font-mono text-destructive">{requireType}</span> to confirm</Label>
            <Input
              value={typed}
              onChange={(e) => setTyped(e.target.value)}
              placeholder={requireType}
              autoComplete="off"
            />
          </div>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
            Cancel
          </Button>
          <Button
            variant={danger ? 'destructive' : 'default'}
            disabled={!canConfirm}
            loading={loading}
            onClick={() => {
              onConfirm()
            }}
          >
            {confirmText}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
