/**
 * Login Component for BuildRunner 3.2
 *
 * Provides user authentication UI with form validation and error handling.
 * Supports login and user session management.
 */

import React, { useState, useEffect } from 'react';
import './Login.css';

interface LoginFormData {
  email: string;
  password: string;
}

interface LoginResponse {
  token: string;
  token_type: string;
  expires_at: string;
}

interface AuthContextType {
  isAuthenticated: boolean;
  user: any;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

interface LoginProps {
  onLoginSuccess?: (token: string) => void;
  onLoginError?: (error: string) => void;
}

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export function Login({ onLoginSuccess, onLoginError }: LoginProps) {
  const [formData, setFormData] = useState<LoginFormData>({
    email: '',
    password: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);

  // Load saved email if remember me was checked
  useEffect(() => {
    const savedEmail = localStorage.getItem('buildrunner_saved_email');
    const savedRemember = localStorage.getItem('buildrunner_remember_me');

    if (savedEmail && savedRemember === 'true') {
      setFormData((prev) => ({ ...prev, email: savedEmail }));
      setRememberMe(true);
    }
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setError('');
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const validateForm = (): boolean => {
    if (!formData.email) {
      setError('Email is required');
      return false;
    }

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      setError('Invalid email format');
      return false;
    }

    if (!formData.password) {
      setError('Password is required');
      return false;
    }

    if (formData.password.length < 6) {
      setError('Password must be at least 6 characters');
      return false;
    }

    return true;
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: formData.email,
          password: formData.password,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Login failed');
      }

      const data: LoginResponse = await response.json();

      // Save token
      localStorage.setItem('buildrunner_token', data.token);
      localStorage.setItem('buildrunner_token_type', data.token_type);
      localStorage.setItem('buildrunner_token_expires', data.expires_at);

      // Save email if remember me is checked
      if (rememberMe) {
        localStorage.setItem('buildrunner_saved_email', formData.email);
        localStorage.setItem('buildrunner_remember_me', 'true');
      } else {
        localStorage.removeItem('buildrunner_saved_email');
        localStorage.removeItem('buildrunner_remember_me');
      }

      // Call success callback
      if (onLoginSuccess) {
        onLoginSuccess(data.token);
      }

      // Redirect or update app state
      window.location.href = '/dashboard';
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An error occurred';
      setError(errorMessage);

      if (onLoginError) {
        onLoginError(errorMessage);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = () => {
    // Implementation for password reset
    alert('Password reset functionality coming soon');
  };

  return (
    <div className="login-container">
      <div className="login-box">
        <div className="login-header">
          <h1>BuildRunner</h1>
          <p>Sign in to your account</p>
        </div>

        {error && <div className="login-error">{error}</div>}

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="email">Email Address</label>
            <input
              id="email"
              type="email"
              name="email"
              value={formData.email}
              onChange={handleInputChange}
              placeholder="you@example.com"
              disabled={loading}
              autoComplete="email"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <div className="password-input-wrapper">
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                name="password"
                value={formData.password}
                onChange={handleInputChange}
                placeholder="Enter your password"
                disabled={loading}
                autoComplete="current-password"
                required
              />
              <button
                type="button"
                className="toggle-password"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? '🙈' : '👁️'}
              </button>
            </div>
          </div>

          <div className="form-group checkbox">
            <input
              id="rememberMe"
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              disabled={loading}
            />
            <label htmlFor="rememberMe">Remember me</label>
          </div>

          <button
            type="submit"
            className="login-button"
            disabled={loading}
          >
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        <div className="login-footer">
          <button
            type="button"
            className="forgot-password"
            onClick={handleForgotPassword}
            disabled={loading}
          >
            Forgot password?
          </button>
        </div>

        <div className="login-info">
          <p>Demo credentials:</p>
          <p>Email: admin@buildrunner.local</p>
          <p>Password: admin</p>
        </div>
      </div>

      <div className="login-background">
        <div className="gradient-blob gradient-blob-1"></div>
        <div className="gradient-blob gradient-blob-2"></div>
        <div className="gradient-blob gradient-blob-3"></div>
      </div>
    </div>
  );
}

// Auth context for global state management
export const AuthContext = React.createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: React.ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<any>(null);

  // Check if user is already authenticated on mount
  useEffect(() => {
    const token = localStorage.getItem('buildrunner_token');
    if (token) {
      // Verify token with backend
      verifyToken(token);
    }
  }, []);

  const verifyToken = async (token: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/verify`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
        setIsAuthenticated(true);
      } else {
        // Token is invalid
        localStorage.removeItem('buildrunner_token');
        setIsAuthenticated(false);
      }
    } catch (error) {
      console.error('Error verifying token:', error);
      setIsAuthenticated(false);
    }
  };

  const login = async (email: string, password: string) => {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Login failed');
    }

    const data = await response.json();
    localStorage.setItem('buildrunner_token', data.token);
    setIsAuthenticated(true);

    // Fetch user info
    await verifyToken(data.token);
  };

  const logout = () => {
    localStorage.removeItem('buildrunner_token');
    localStorage.removeItem('buildrunner_token_type');
    localStorage.removeItem('buildrunner_token_expires');
    setUser(null);
    setIsAuthenticated(false);
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

// Hook to use auth context
export function useAuth() {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}

// Protected route component
interface ProtectedRouteProps {
  children: React.ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <Login />;
  }

  return <>{children}</>;
}
