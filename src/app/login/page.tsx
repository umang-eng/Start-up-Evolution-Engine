'use client';

import React, { useState } from 'react';
import { useAuth } from '@/components/shared/auth-provider';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import Link from 'next/link';
import { Sparkles, KeyRound, Mail, AlertCircle, ArrowRight } from 'lucide-react';

export default function LoginPage() {
  const { login, error, setError } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;

    setIsSubmitting(true);
    try {
      await login(email, password);
    } catch (err) {
      // Error is handled by AuthProvider and displayed in the UI
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="h-screen w-screen flex items-center justify-center bg-mesh-hero font-sans relative overflow-hidden">
      {/* Dynamic Background Glowing Orbs */}
      <div className="absolute top-[-20%] left-[-15%] w-[50%] h-[50%] rounded-full blur-[140px] pointer-events-none" style={{ background: 'hsla(192, 91%, 54%, 0.08)' }} />
      <div className="absolute bottom-[-20%] right-[-15%] w-[50%] h-[50%] rounded-full blur-[140px] pointer-events-none" style={{ background: 'hsla(262, 83%, 68%, 0.06)' }} />

      <div className="w-full max-w-md px-4 z-10">
        <Card className="border-white/[0.06] bg-card/80 backdrop-blur-xl shadow-lvl-3">
          <CardHeader className="space-y-3 text-center pb-6">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl overflow-hidden border border-white/[0.08] bg-white/[0.03] shadow-lvl-1 glow-cyan">
              <img src="/logo.png" alt="Evolution Engine Logo" className="h-full w-full object-cover" />
            </div>
            <CardTitle className="text-2xl font-bold tracking-tight text-foreground">Welcome Back</CardTitle>
            <CardDescription className="text-sm text-muted-foreground">
              Sign in to manage your startup blueprints and pipeline
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {error && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm flex items-center gap-2">
                <AlertCircle className="h-5 w-5 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-3 h-5 w-5 text-muted-foreground/80" />
                  <Input
                    type="email"
                    placeholder="name@company.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="pl-9 h-10 text-sm bg-white/[0.03] border-white/[0.06] text-foreground placeholder-muted-foreground/30"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
                    Password
                  </label>
                  <Link
                    href="/forgot-password"
                    className="text-sm text-cyan-400 hover:underline font-medium"
                  >
                    Forgot password?
                  </Link>
                </div>
                <div className="relative">
                  <KeyRound className="absolute left-3 top-3 h-5 w-5 text-muted-foreground/80" />
                  <Input
                    type="password"
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="pl-9 h-10 text-sm bg-white/[0.03] border-white/[0.06] text-foreground placeholder-muted-foreground/30"
                  />
                </div>
              </div>

              <Button
                type="submit"
                disabled={isSubmitting}
                className="w-full h-10 mt-2 text-sm font-medium flex items-center justify-center gap-1.5"
              >
                <span>{isSubmitting ? 'Signing in...' : 'Sign In'}</span>
                {!isSubmitting && <ArrowRight className="h-5 w-5" />}
              </Button>
            </form>

            <div className="text-center pt-4 border-t border-white/[0.04]">
              <span className="text-sm text-muted-foreground">
                Don&apos;t have an account?{' '}
                <Link
                  href="/signup"
                  onClick={() => setError(null)}
                  className="text-cyan-400 font-semibold hover:underline"
                >
                  Create one
                </Link>
              </span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
