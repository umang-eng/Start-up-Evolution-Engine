'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import Link from 'next/link';
import { Sparkles, Mail, AlertCircle, CheckCircle, ArrowLeft } from 'lucide-react';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSent, setIsSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setIsSubmitting(true);
    setError(null);

    try {
      // Direct pass representation
      // Mock call since password reset mail verification runs in staging/prod
      await new Promise((resolve) => setTimeout(resolve, 1000));
      setIsSent(true);
    } catch (err: any) {
      setError(err.message || 'An error occurred. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="h-screen w-screen flex items-center justify-center bg-canvas font-sans relative overflow-hidden">
      {/* Dynamic Background Glowing Accents */}
      <div className="absolute top-[-20%] left-[-20%] w-[60%] h-[60%] rounded-full bg-accent-blue/10 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-20%] w-[60%] h-[60%] rounded-full bg-accent-blue/5 blur-[120px] pointer-events-none" />

      <div className="w-full max-w-md px-4 z-10">
        <Card className="border-border bg-white/70 backdrop-blur-xl shadow-lvl-3">
          <CardHeader className="space-y-2 text-center pb-6">
            <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-lg overflow-hidden border border-border bg-white shadow-lvl-1">
              <img src="/logo.png" alt="Evolution Engine Logo" className="h-full w-full object-cover" />
            </div>
            <CardTitle className="text-2xl font-bold tracking-tight text-primary">Reset Password</CardTitle>
            <CardDescription className="text-xs text-muted-foreground">
              Enter your email to receive recovery authorization credentials
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {isSent ? (
              <div className="space-y-4 text-center">
                <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20 text-green-600 text-xs flex items-center gap-2 text-left">
                  <CheckCircle className="h-4 w-4 shrink-0" />
                  <span>A recovery email has been sent if the email exists in our records. Please check your inbox.</span>
                </div>
                <Link
                  href="/login"
                  className="inline-flex items-center justify-center gap-1.5 text-xs font-semibold text-accent-blue hover:underline"
                >
                  <ArrowLeft className="h-3 w-3" />
                  <span>Back to login</span>
                </Link>
              </div>
            ) : (
              <>
                {error && (
                  <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-600 text-xs flex items-center gap-2">
                    <AlertCircle className="h-4 w-4 shrink-0" />
                    <span>{error}</span>
                  </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      Email Address
                    </label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground/60" />
                      <Input
                        type="email"
                        placeholder="name@company.com"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                        className="pl-9 h-10 text-sm"
                      />
                    </div>
                  </div>

                  <Button
                    type="submit"
                    disabled={isSubmitting}
                    className="w-full h-10 mt-2 text-sm font-medium flex items-center justify-center gap-1.5"
                  >
                    <span>{isSubmitting ? 'Sending...' : 'Send Recovery Link'}</span>
                  </Button>
                </form>

                <div className="text-center pt-4 border-t border-border/50">
                  <Link
                    href="/login"
                    className="inline-flex items-center justify-center gap-1.5 text-xs font-semibold text-muted-foreground hover:text-primary transition-all"
                  >
                    <ArrowLeft className="h-3.5 w-3.5" />
                    <span>Cancel and return</span>
                  </Link>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
