import { useState, useEffect, useRef } from 'react';
import { ShieldCheck, ChevronDown, Loader2, ArrowRight, LogOut } from 'lucide-react';
import { getTermsContent } from '../authApi';
import Logo from './Logo';

/**
 * TermsGate — Full-screen Terms & Conditions acceptance screen.
 * 
 * Shown to authenticated users who haven't yet accepted T&C.
 * This is separate from the Auth component modal — it's a dedicated
 * blocking screen that appears after login for returning users.
 */
export default function TermsGate({ onAccept, onDecline }) {
  const [termsContent, setTermsContent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [hasScrolledToBottom, setHasScrolledToBottom] = useState(false);
  const [accepting, setAccepting] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    getTermsContent()
      .then(setTermsContent)
      .catch(() =>
        setTermsContent({
          title: 'Terms & Conditions',
          version: '1.0',
          last_updated: 'N/A',
          sections: [{ heading: 'Error', body: 'Could not load terms. Please try again later.' }],
        })
      )
      .finally(() => setLoading(false));
  }, []);

  const handleScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    if (atBottom) setHasScrolledToBottom(true);
  };

  const handleAccept = async () => {
    setAccepting(true);
    try {
      await onAccept();
    } catch {
      setAccepting(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-[var(--bg-base)] text-[var(--text-primary)] px-4 relative overflow-hidden">
      {/* Background Decorative */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-[-15%] right-[-5%] w-[400px] h-[400px] rounded-full bg-[var(--color-quant-orange)] opacity-[0.03] blur-[80px]" />
        <div className="absolute bottom-[-15%] left-[-5%] w-[350px] h-[350px] rounded-full bg-[var(--color-quant-indigo)] opacity-[0.03] blur-[80px]" />
      </div>

      {/* Logo */}
      <div className="flex items-center gap-3 mb-8 z-10">
        <div className="w-10 h-10 rounded-xl bg-[var(--color-quant-orange)] border-2 border-[var(--border-subtle)] flex items-center justify-center shadow-[var(--shadow-sm)] overflow-hidden">
          <Logo size={36} />
        </div>
        <span className="font-display text-3xl font-semibold tracking-tight">QuantPilot</span>
      </div>

      {/* Main Card */}
      <div className="relative z-10 w-full max-w-2xl max-h-[80vh] bg-[var(--bg-surface-elevated)] rounded-[24px] border-2 border-[var(--border-subtle)] shadow-[var(--shadow-elevated)] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-6 sm:px-8 py-5 border-b-2 border-[var(--border-subtle)] shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[var(--color-quant-orange)] flex items-center justify-center border-2 border-[var(--border-subtle)] shadow-[var(--shadow-sm)]">
              <ShieldCheck size={18} className="text-white" />
            </div>
            <div>
              <h2 className="font-display text-xl font-black uppercase tracking-tight">
                Accept Terms to Continue
              </h2>
              {termsContent && (
                <p className="text-[10px] font-mono text-[var(--text-tertiary)] mt-0.5">
                  Version {termsContent.version} · Updated {termsContent.last_updated}
                </p>
              )}
            </div>
          </div>
          <p className="mt-3 font-mono text-xs text-[var(--text-secondary)]">
            Please review and accept our Terms & Conditions to access QuantPilot.
          </p>
        </div>

        {/* Scrollable Terms Content */}
        <div
          ref={scrollRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto px-6 sm:px-8 py-6"
        >
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 size={24} className="animate-spin text-[var(--color-quant-orange)]" />
              <span className="ml-3 font-mono text-sm text-[var(--text-secondary)]">Loading terms...</span>
            </div>
          ) : termsContent ? (
            <div className="space-y-6">
              {termsContent.sections.map((section, idx) => (
                <div key={idx}>
                  <h3 className="font-mono text-sm font-bold text-[var(--text-primary)] mb-2 uppercase tracking-wide">
                    {section.heading}
                  </h3>
                  <p className="text-sm text-[var(--text-secondary)] leading-relaxed font-sans">
                    {section.body}
                  </p>
                </div>
              ))}

              {!hasScrolledToBottom && (
                <div className="sticky bottom-0 left-0 right-0 flex justify-center pb-2 pt-6 bg-gradient-to-t from-[var(--bg-surface-elevated)] to-transparent">
                  <div className="flex items-center gap-1.5 text-[10px] font-mono text-[var(--text-tertiary)] animate-bounce">
                    <ChevronDown size={14} />
                    <span>Scroll to read all terms</span>
                  </div>
                </div>
              )}
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="px-6 sm:px-8 py-4 border-t-2 border-[var(--border-subtle)] shrink-0 flex items-center justify-between gap-3">
          <button
            onClick={onDecline}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl font-mono text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] bg-[var(--bg-surface)] border-2 border-[var(--border-subtle)] hover:bg-[var(--bg-surface-hover)] transition-colors cursor-pointer shadow-[var(--shadow-sm)] active:translate-y-[2px] active:translate-x-[2px] active:shadow-none"
          >
            <LogOut size={14} />
            <span>Decline & Sign Out</span>
          </button>
          <button
            onClick={handleAccept}
            disabled={accepting || (!hasScrolledToBottom && termsContent?.sections?.length > 3)}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl font-mono text-xs font-bold uppercase tracking-wider text-white bg-[var(--color-quant-orange)] border-2 border-[var(--border-subtle)] hover:bg-orange-600 transition-all cursor-pointer shadow-[var(--shadow-sm)] active:translate-y-[2px] active:translate-x-[2px] active:shadow-none disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {accepting ? (
              <>
                <Loader2 size={14} className="animate-spin" />
                <span>Accepting...</span>
              </>
            ) : (
              <>
                <ShieldCheck size={14} />
                <span>I Accept</span>
                <ArrowRight size={14} />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
