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
      <div className="p-8 bg-[var(--bg-surface-elevated)] rounded-2xl border border-[var(--border-subtle)] shadow-xl w-full max-w-md text-center">
        <h1 className="text-2xl font-bold mb-6">
          {isLogin ? 'Welcome Back' : 'Create an Account'}
        </h1>
        <p className="text-sm text-[var(--text-secondary)] mb-8">
          Sign in to access QuantPilot AI.
        </p>

        <button
          onClick={handleGoogleLogin}
          disabled={loading}
          className="w-full flex items-center justify-center gap-3 bg-white text-gray-800 font-bold py-3 px-4 rounded-xl shadow-md hover:bg-gray-50 transition-colors border border-gray-200 cursor-pointer"
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
