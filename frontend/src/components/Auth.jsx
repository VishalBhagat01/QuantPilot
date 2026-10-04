import { useState } from 'react';
import { supabase } from '../supabaseClient';

export default function Auth() {
  const [loading, setLoading] = useState(false);
  const [isLogin, setIsLogin] = useState(true);

  const handleGoogleLogin = async () => {
    try {
      setLoading(true);
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
      });
      if (error) throw error;
    } catch (error) {
      alert(error.error_description || error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center h-screen bg-[var(--bg-base)] text-[var(--text-primary)]">
      <div className="p-10 bg-[var(--bg-surface-elevated)] rounded-[24px] border-2 border-[var(--border-subtle)] shadow-[var(--shadow-card)] w-full max-w-md text-center">
        <h1 className="font-display text-3xl font-black uppercase tracking-tight mb-4">
          {isLogin ? 'Welcome Back' : 'Create an Account'}
        </h1>
        <p className="font-mono text-sm text-[var(--text-secondary)] mb-8">
          Sign in to access QuantPilot AI.
        </p>

        <button
          onClick={handleGoogleLogin}
          disabled={loading}
          className="w-full flex items-center justify-center gap-3 bg-[var(--bg-surface)] text-[var(--text-primary)] font-mono font-bold uppercase tracking-wider py-3.5 px-4 rounded-xl shadow-[var(--shadow-sm)] hover:bg-[var(--bg-surface-hover)] transition-colors border-2 border-[var(--border-subtle)] cursor-pointer"
        >
          <img src="https://www.svgrepo.com/show/475656/google-color.svg" alt="Google Logo" className="w-5 h-5" />
          {loading ? 'Redirecting...' : 'Continue with Google'}
        </button>

        <div className="mt-6 flex items-center justify-between text-xs text-[var(--text-tertiary)] w-full">
            <span className="w-1/3 border-b border-[var(--border-subtle)]"></span>
            <span className="cursor-pointer hover:text-[var(--text-primary)]" onClick={() => setIsLogin(!isLogin)}>
                {isLogin ? 'Need an account? Register' : 'Have an account? Login'}
            </span>
            <span className="w-1/3 border-b border-[var(--border-subtle)]"></span>
        </div>
      </div>
    </div>
  );
}
