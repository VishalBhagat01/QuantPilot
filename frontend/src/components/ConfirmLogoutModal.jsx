import { useEffect, useRef, useState } from "react"
import { AlertTriangle, Check, Loader2, X } from "lucide-react"

export default function ConfirmLogoutModal({ isOpen, onCancel, onConfirm, isSubmitting = false }) {
  const [isAcknowledged, setIsAcknowledged] = useState(false)
  const cancelButtonRef = useRef(null)

  useEffect(() => {
    if (!isOpen) return

    cancelButtonRef.current?.focus()

    const handleKeyDown = (event) => {
      if (event.key === "Escape" && !isSubmitting) {
        onCancel()
      }
    }

    document.addEventListener("keydown", handleKeyDown)
    return () => document.removeEventListener("keydown", handleKeyDown)
  }, [isOpen, isSubmitting, onCancel])

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/65 px-4 backdrop-blur-sm"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !isSubmitting) onCancel()
      }}
    >
      <section
        className="w-full max-w-md rounded-2xl border-2 border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 text-[var(--text-primary)] shadow-[var(--shadow-elevated)]"
        role="dialog"
        aria-modal="true"
        aria-labelledby="logout-modal-title"
        aria-describedby="logout-modal-description"
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border-2 border-[var(--border-subtle)] bg-orange-500/10 text-[var(--color-quant-orange)]">
              <AlertTriangle size={20} />
            </div>
            <div>
              <h2 id="logout-modal-title" className="text-lg font-bold tracking-tight">
                Confirm logout
              </h2>
              <p id="logout-modal-description" className="mt-1 text-sm leading-relaxed text-[var(--text-secondary)]">
                Are you sure you want to log out of your QuantPilot session?
              </p>
            </div>
          </div>
          <button
            ref={cancelButtonRef}
            type="button"
            onClick={onCancel}
            disabled={isSubmitting}
            className="rounded-lg p-1.5 text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-surface-hover)] hover:text-[var(--text-primary)] disabled:cursor-not-allowed disabled:opacity-50"
            aria-label="Close logout confirmation"
          >
            <X size={18} />
          </button>
        </div>

        <label className="mt-6 flex cursor-pointer items-start gap-3 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface-elevated)] p-3 text-sm text-[var(--text-secondary)]">
          <input
            type="checkbox"
            checked={isAcknowledged}
            onChange={(event) => setIsAcknowledged(event.target.checked)}
            disabled={isSubmitting}
            className="peer sr-only"
          />
          <span
            aria-hidden="true"
            className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md border-2 transition-colors ${
              isAcknowledged
                ? "border-[var(--color-quant-orange)] bg-[var(--color-quant-orange)] text-white"
                : "border-[var(--text-tertiary)] bg-[var(--bg-surface)]"
            }`}
          >
            {isAcknowledged && <Check size={13} strokeWidth={3} />}
          </span>
          <span>I understand that logging out will end my current session.</span>
        </label>

        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            disabled={isSubmitting}
            className="rounded-xl border-2 border-[var(--border-subtle)] bg-[var(--bg-surface)] px-4 py-2 text-sm font-bold text-[var(--text-primary)] transition-colors hover:bg-[var(--bg-surface-hover)] disabled:cursor-not-allowed disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={!isAcknowledged || isSubmitting}
            className="flex items-center gap-2 rounded-xl border-2 border-[var(--border-subtle)] bg-[var(--color-quant-orange)] px-4 py-2 text-sm font-bold text-white transition-colors hover:bg-orange-600 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isSubmitting && <Loader2 size={15} className="animate-spin" />}
            {isSubmitting ? "Logging out..." : "Log out"}
          </button>
        </div>
      </section>
    </div>
  )
}
