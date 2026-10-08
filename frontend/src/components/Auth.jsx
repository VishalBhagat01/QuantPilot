import { useState, useEffect, useRef } from 'react';
import { ShieldCheck, ChevronDown, Loader2, Terminal, ArrowRight } from 'lucide-react';
import { startGoogleOAuth, getTermsContent } from '../authApi';

/**
 * Auth Component — Login screen with Terms & Conditions gate.
 *
 * OAuth flow:
 *   1. User accepts T&C
 *   2. Clicks "Continue with Google"
 *   3. Supabase PKCE flow starts (client-side — required for code_verifier)
 *   4. Google redirects back → Supabase detects session → App.jsx captures it
 *   5. Backend validates token + records T&C acceptance
 */
export default function Auth() {
  const [loading, setLoading] = useState(false);
  const [showTerms, setShowTerms] = useState(false);
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [termsContent, setTermsContent] = useState(null);
  const [termsLoading, setTermsLoading] = useState(false);
  const [hasScrolledToBottom, setHasScrolledToBottom] = useState(false);
  const termsScrollRef = useRef(null);

  // Fetch T&C content from backend when modal opens
  useEffect(() => {
    if (showTerms && !termsContent) {
      setTermsLoading(true);
      getTermsContent()
        .then((data) => setTermsContent(data))
        .catch(() => setTermsContent({ title: 'Terms & Conditions', sections: [{ heading: 'Error', body: 'Could not load terms. Please try again.' }] }))
        .finally(() => setTermsLoading(false));
    }
  }, [showTerms, termsContent]);

  // Track scroll position in terms modal
  const handleTermsScroll = () => {
    const el = termsScrollRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    if (atBottom) setHasScrolledToBottom(true);
  };

  const handleGoogleLogin = async () => {
    if (!termsAccepted) {
      setShowTerms(true);
      return;
    }

    try {
      setLoading(true);
      // Uses Supabase client-side SDK for PKCE OAuth (backend validates after)
      await startGoogleOAuth();
    } catch (error) {
      alert(error.error_description || error.message || 'Failed to start login');
      setLoading(false);
    }
  };

  const handleAcceptTerms = () => {
    setTermsAccepted(true);
    setShowTerms(false);
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-[var(--bg-base)] text-[var(--text-primary)] px-4 relative overflow-hidden">
      {/* Background Decorative Elements */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-[-20%] left-[-10%] w-[500px] h-[500px] rounded-full bg-[var(--color-quant-orange)] opacity-[0.03] blur-[100px]" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[400px] h-[400px] rounded-full bg-[var(--color-quant-indigo)] opacity-[0.03] blur-[100px]" />
      </div>

      {/* Logo & Branding */}
      <div className="flex items-center gap-3 mb-10 z-10">
        <div className="w-10 h-10 rounded-xl bg-[var(--color-quant-orange)] border-2 border-[var(--border-subtle)] flex items-center justify-center shadow-[var(--shadow-sm)]">
          <Terminal size={20} className="text-white" />
        </div>
        <div className="flex items-center gap-2">
          <span className="font-display text-2xl tracking-tight font-black text-[var(--text-primary)]">
            quantpilot
          </span>
          <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-[var(--bg-surface-elevated)] border border-[var(--border-subtle)] text-[var(--text-secondary)]">
            [agent]
          </span>
        </div>
      </div>

      {/* Main Auth Card */}
      <div className="relative z-10 p-8 sm:p-10 bg-[var(--bg-surface-elevated)] rounded-[24px] border-2 border-[var(--border-subtle)] shadow-[var(--shadow-elevated)] w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="font-display text-3xl font-black uppercase tracking-tight mb-3">
            Welcome
          </h1>
          <p className="font-mono text-sm text-[var(--text-secondary)] leading-relaxed">
            Sign in to access QuantPilot AI — your institutional financial intelligence terminal.
          </p>
        </div>

        {/* T&C Checkbox */}
        <div className="mb-6">
          <label className="flex items-start gap-3 cursor-pointer group" onClick={(e) => {
            e.preventDefault();
            if (!termsAccepted) {
              setShowTerms(true);
            } else {
              setTermsAccepted(false);
            }
          }}>
            <div className={`mt-0.5 w-5 h-5 rounded-md border-2 flex items-center justify-center shrink-0 transition-all duration-200 ${
              termsAccepted 
                ? 'bg-[var(--color-quant-orange)] border-[var(--color-quant-orange)]' 
                : 'border-[var(--border-subtle)] bg-[var(--bg-surface)] group-hover:border-[var(--text-tertiary)]'
            }`}>
              {termsAccepted && (
                <svg width="12" height="10" viewBox="0 0 12 10" fill="none">
                  <path d="M1 5L4.5 8.5L11 1.5" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              )}
            </div>
            <span className="text-xs font-mono text-[var(--text-secondary)] leading-relaxed">
              I have read and agree to the{' '}
              <span 
                className="text-[var(--color-quant-orange)] underline underline-offset-2 hover:text-orange-400 transition-colors"
                onClick={(e) => {
                  e.stopPropagation();
                  setShowTerms(true);
                }}
              >
                Terms & Conditions
              </span>
            </span>
          </label>
        </div>

        {/* Google Login Button */}
        <button
          onClick={handleGoogleLogin}
          disabled={loading}
          className={`w-full flex items-center justify-center gap-3 font-mono font-bold uppercase tracking-wider py-3.5 px-4 rounded-xl shadow-[var(--shadow-sm)] transition-all border-2 cursor-pointer ${
            termsAccepted
              ? 'bg-[var(--color-quant-orange)] text-white border-[var(--border-subtle)] hover:bg-orange-600 active:translate-y-[2px] active:translate-x-[2px] active:shadow-none'
              : 'bg-[var(--bg-surface)] text-[var(--text-primary)] border-[var(--border-subtle)] hover:bg-[var(--bg-surface-hover)]'
          }`}
        >
          <img src="https://www.svgrepo.com/show/475656/google-color.svg" alt="Google Logo" className="w-5 h-5" />
          {loading ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              <span className="text-sm">Redirecting...</span>
            </>
          ) : (
            <span className="text-sm">Continue with Google</span>
          )}
        </button>

        {!termsAccepted && (
          <p className="mt-3 text-center text-[10px] font-mono text-[var(--text-tertiary)]">
            Please accept Terms & Conditions to continue
          </p>
        )}

        {/* Divider */}
        <div className="mt-8 flex items-center gap-3">
          <span className="flex-1 border-b border-[var(--border-subtle)]" />
          <span className="text-[10px] font-mono text-[var(--text-tertiary)] uppercase tracking-widest">Secured</span>
          <span className="flex-1 border-b border-[var(--border-subtle)]" />
        </div>

        <div className="mt-4 flex items-center justify-center gap-2 text-[10px] font-mono text-[var(--text-tertiary)]">
          <ShieldCheck size={12} className="text-emerald-500" />
          <span>Session validated server-side · T&C enforced by backend</span>
        </div>
      </div>

      {/* ═══════════════ Terms & Conditions Modal ═══════════════ */}
      {showTerms && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          {/* Backdrop */}
          <div 
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            onClick={() => setShowTerms(false)}
          />

          {/* Modal */}
          <div className="relative z-10 w-full max-w-2xl max-h-[85vh] bg-[var(--bg-surface-elevated)] rounded-[24px] border-2 border-[var(--border-subtle)] shadow-[var(--shadow-elevated)] flex flex-col overflow-hidden">
            {/* Header */}
            <div className="px-6 sm:px-8 py-5 border-b-2 border-[var(--border-subtle)] shrink-0">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-[var(--color-quant-orange)] flex items-center justify-center border-2 border-[var(--border-subtle)] shadow-[var(--shadow-sm)]">
                  <ShieldCheck size={18} className="text-white" />
                </div>
                <div>
                  <h2 className="font-display text-xl font-black uppercase tracking-tight text-[var(--text-primary)]">
                    Terms & Conditions
                  </h2>
                  {termsContent && (
                    <p className="text-[10px] font-mono text-[var(--text-tertiary)] mt-0.5">
                      Version {termsContent.version} · Last updated {termsContent.last_updated}
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* Scrollable Content */}
            <div 
              ref={termsScrollRef}
              onScroll={handleTermsScroll}
              className="flex-1 overflow-y-auto px-6 sm:px-8 py-6"
            >
              {termsLoading ? (
                <div className="flex items-center justify-center py-20">
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

                  {/* Scroll indicator */}
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

            {/* Footer Actions */}
            <div className="px-6 sm:px-8 py-4 border-t-2 border-[var(--border-subtle)] shrink-0 flex items-center justify-between gap-3">
              <button
                onClick={() => setShowTerms(false)}
                className="px-5 py-2.5 rounded-xl font-mono text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)] bg-[var(--bg-surface)] border-2 border-[var(--border-subtle)] hover:bg-[var(--bg-surface-hover)] transition-colors cursor-pointer shadow-[var(--shadow-sm)] active:translate-y-[2px] active:translate-x-[2px] active:shadow-none"
              >
                Decline
              </button>
              <button
                onClick={handleAcceptTerms}
                disabled={!hasScrolledToBottom && termsContent?.sections?.length > 3}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl font-mono text-xs font-bold uppercase tracking-wider text-white bg-[var(--color-quant-orange)] border-2 border-[var(--border-subtle)] hover:bg-orange-600 transition-all cursor-pointer shadow-[var(--shadow-sm)] active:translate-y-[2px] active:translate-x-[2px] active:shadow-none disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <ShieldCheck size={14} />
                <span>I Accept</span>
                <ArrowRight size={14} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
