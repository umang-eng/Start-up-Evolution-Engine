'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { api, getAccessToken, clearTokens, setTokens } from '@/lib/api-client';

interface User {
  id: string;
  email: string;
  role: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  logout: () => void;
  error: string | null;
  setError: (err: string | null) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const PUBLIC_PATHS = ['/login', '/signup', '/forgot-password', '/reset-password'];

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const pathname = usePathname();

  const loadUser = async () => {
    const token = getAccessToken();
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    try {
      const profile = await api.auth.me();
      setUser(profile);
    } catch (err: any) {
      console.error('Failed to load user profile on mount:', err);
      clearTokens();
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadUser();
  }, []);

  // Secure path redirects
  useEffect(() => {
    if (isLoading) return;

    // Check if the user is on a public page or is accessing a shared link (e.g. /shared/token)
    const isPublicPath = PUBLIC_PATHS.some(path => pathname.startsWith(path)) || pathname.startsWith('/shared');
    
    if (!user && !isPublicPath) {
      router.push('/login');
    } else if (user && isPublicPath && PUBLIC_PATHS.includes(pathname)) {
      router.push('/');
    }
  }, [user, pathname, isLoading, router]);

  const login = async (email: string, password: string) => {
    setError(null);
    try {
      const response = await api.auth.login({ email, password });
      setTokens(response.access_token, response.refresh_token);
      const profile = await api.auth.me();
      setUser(profile);
      router.push('/');
    } catch (err: any) {
      setError(err.message || 'Login failed. Please check your credentials.');
      throw err;
    }
  };

  const signup = async (email: string, password: string) => {
    setError(null);
    try {
      await api.auth.register({ email, password });
      // Log in automatically after registration
      await login(email, password);
    } catch (err: any) {
      setError(err.message || 'Registration failed. Please try again.');
      throw err;
    }
  };

  const logout = () => {
    clearTokens();
    setUser(null);
    router.push('/login');
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        signup,
        logout,
        error,
        setError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
