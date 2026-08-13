"use client"

import {
  Check,
  Copy,
  KeyRound,
  Loader2,
  Plus,
  RefreshCw,
  Trash2,
} from "lucide-react"
import { useCallback, useEffect, useState } from "react"

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { useToast } from "@/hooks/use-toast"

const API_ROOT = "/api/proxy/api/v1/document-extractions/api-keys"

interface ApiKeyMetadata {
  id: string
  name: string
  key_prefix: string
  created_at: string
  last_used_at: string | null
  revoked_at: string | null
}

interface ApiKeyCreated extends ApiKeyMetadata {
  api_key: string
}

type PendingAction = { type: "rotate" | "revoke"; key: ApiKeyMetadata } | null

async function responseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as {
      detail?: string
    } | null
    throw new Error(body?.detail ?? `Request failed with status ${response.status}`)
  }
  return (await response.json()) as T
}

function dateLabel(value: string | null): string {
  if (!value) return "Never"
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value))
}

export default function ApiKeys() {
  const showToast = useToast()
  const [keys, setKeys] = useState<ApiKeyMetadata[]>([])
  const [name, setName] = useState("Document extraction")
  const [revealed, setRevealed] = useState<ApiKeyCreated | null>(null)
  const [pendingAction, setPendingAction] = useState<PendingAction>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadKeys = useCallback(async () => {
    try {
      const response = await fetch(API_ROOT, { cache: "no-store" })
      setKeys(await responseJson<ApiKeyMetadata[]>(response))
      setError(null)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "API keys could not be loaded")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadKeys()
  }, [loadKeys])

  async function createKey() {
    const trimmedName = name.trim()
    if (!trimmedName) return
    setBusy(true)
    setError(null)
    try {
      const response = await fetch(API_ROOT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: trimmedName }),
      })
      const created = await responseJson<ApiKeyCreated>(response)
      setRevealed(created)
      setCopied(false)
      setName("Document extraction")
      await loadKeys()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "API key could not be created")
    } finally {
      setBusy(false)
    }
  }

  async function confirmAction() {
    if (!pendingAction) return
    const action = pendingAction
    setBusy(true)
    setError(null)
    try {
      if (action.type === "rotate") {
        const response = await fetch(`${API_ROOT}/${action.key.id}/rotate`, {
          method: "POST",
        })
        const created = await responseJson<ApiKeyCreated>(response)
        setRevealed(created)
        setCopied(false)
        showToast(
          "API key rotated",
          "The previous key was revoked. Save the replacement now.",
          "success",
        )
      } else {
        const response = await fetch(`${API_ROOT}/${action.key.id}`, {
          method: "DELETE",
        })
        if (!response.ok) await responseJson(response)
        showToast("API key revoked", "The key can no longer authenticate requests.", "success")
      }
      setPendingAction(null)
      await loadKeys()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "API key could not be updated")
    } finally {
      setBusy(false)
    }
  }

  async function copySecret() {
    if (!revealed) return
    try {
      await navigator.clipboard.writeText(revealed.api_key)
      setCopied(true)
      showToast("Copied", "The API key was copied to your clipboard.", "success")
    } catch {
      showToast("Copy failed", "Select and copy the API key manually.", "error")
    }
  }

  const activeKeys = keys.filter((key) => !key.revoked_at)
  const revokedKeys = keys.filter((key) => key.revoked_at)

  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <h3 className="text-sm font-semibold">Document extraction API keys</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          Use API keys for server-to-server uploads to the document extraction API.
          Never expose a key in browser code or source control.
        </p>
      </div>

      {revealed && (
        <Card className="border-amber-500/50 bg-amber-500/5" role="status">
          <CardHeader>
            <CardTitle className="text-base">Save your API key now</CardTitle>
            <CardDescription>
              This is the only time the complete key will be displayed. If it is lost,
              rotate it to create a replacement.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex flex-col gap-2 sm:flex-row">
              <Input
                aria-label="New API key"
                className="font-mono text-xs"
                readOnly
                value={revealed.api_key}
                onFocus={(event) => event.currentTarget.select()}
              />
              <Button type="button" variant="outline" onClick={() => void copySecret()}>
                {copied ? <Check aria-hidden /> : <Copy aria-hidden />}
                {copied ? "Copied" : "Copy"}
              </Button>
            </div>
            <Button type="button" size="sm" onClick={() => setRevealed(null)}>
              I have saved this key
            </Button>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Create an API key</CardTitle>
          <CardDescription>
            Give each integration its own key so it can be rotated independently.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form
            className="flex flex-col gap-3 sm:flex-row sm:items-end"
            onSubmit={(event) => {
              event.preventDefault()
              void createKey()
            }}
          >
            <div className="w-full space-y-1.5 sm:max-w-sm">
              <Label htmlFor="api-key-name">Key name</Label>
              <Input
                id="api-key-name"
                maxLength={100}
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Production integration"
              />
            </div>
            <Button type="submit" disabled={busy || !name.trim()}>
              {busy ? <Loader2 className="animate-spin" aria-hidden /> : <Plus aria-hidden />}
              Create key
            </Button>
          </form>
        </CardContent>
      </Card>

      {error && (
        <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive" role="alert">
          {error}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Active keys</CardTitle>
          <CardDescription>
            Only a prefix is retained for identification. Complete keys cannot be recovered.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {loading ? (
            <div className="space-y-3">
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-20 w-full" />
            </div>
          ) : activeKeys.length === 0 ? (
            <div className="rounded-md border border-dashed p-8 text-center text-sm text-muted-foreground">
              <KeyRound className="mx-auto mb-2" aria-hidden />
              No active API keys.
            </div>
          ) : (
            activeKeys.map((key) => (
              <div
                key={key.id}
                className="flex flex-col justify-between gap-4 rounded-md border p-4 md:flex-row md:items-center"
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-medium">{key.name}</p>
                    <Badge variant="secondary">Active</Badge>
                  </div>
                  <code className="mt-1 block text-xs text-muted-foreground">
                    {key.key_prefix}••••••••••••
                  </code>
                  <p className="mt-2 text-xs text-muted-foreground">
                    Created {dateLabel(key.created_at)} · Last used {dateLabel(key.last_used_at)}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    disabled={busy}
                    onClick={() => setPendingAction({ type: "rotate", key })}
                  >
                    <RefreshCw aria-hidden />
                    Rotate
                  </Button>
                  <Button
                    type="button"
                    variant="destructive"
                    disabled={busy}
                    onClick={() => setPendingAction({ type: "revoke", key })}
                  >
                    <Trash2 aria-hidden />
                    Revoke
                  </Button>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      {revokedKeys.length > 0 && (
        <details className="rounded-lg border bg-card p-4 text-sm">
          <summary className="cursor-pointer font-medium">
            Revoked keys ({revokedKeys.length})
          </summary>
          <div className="mt-3 space-y-2">
            {revokedKeys.map((key) => (
              <div key={key.id} className="flex flex-wrap justify-between gap-2 border-t pt-2 text-muted-foreground">
                <span>{key.name} · {key.key_prefix}••••</span>
                <span>Revoked {dateLabel(key.revoked_at)}</span>
              </div>
            ))}
          </div>
        </details>
      )}

      <AlertDialog
        open={pendingAction !== null}
        onOpenChange={(open) => {
          if (!open && !busy) setPendingAction(null)
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {pendingAction?.type === "rotate" ? "Rotate this API key?" : "Revoke this API key?"}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {pendingAction?.type === "rotate"
                ? "The current key will stop working immediately. Update the integration with the replacement key after copying it."
                : "This key will stop working immediately. This action cannot be undone."}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={busy}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              disabled={busy}
              className={pendingAction?.type === "revoke" ? "bg-destructive text-destructive-foreground hover:bg-destructive/90" : ""}
              onClick={(event) => {
                event.preventDefault()
                void confirmAction()
              }}
            >
              {busy && <Loader2 className="animate-spin" aria-hidden />}
              {pendingAction?.type === "rotate" ? "Rotate key" : "Revoke key"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
