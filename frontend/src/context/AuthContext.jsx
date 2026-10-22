import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import {
  loginUser,
  registerUser,
  getCurrentUserProfile,
  logoutUser,
  getStoredAuthToken,
  setStoredAuthToken
} from "../services/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => getStoredAuthToken());
  const [loading, setLoading] = useState(true);

  const logout = useCallback(async () => {
    try {
      await logoutUser();
    } catch (_) {
      // Ignore network errors on logout
    } finally {
      setStoredAuthToken(null);
      setToken(null);
      setUser(null);
    }
  }, []);

  // Verify session on mount or token change
  useEffect(() => {
    let isMounted = true;

    async function verifySession() {
      const existingToken = getStoredAuthToken();
      if (!existingToken) {
        if (isMounted) {
          setUser(null);
          setToken(null);
          setLoading(false);
        }
        return;
      }

      try {
        const res = await getCurrentUserProfile();
        if (isMounted && res?.user) {
          setUser(res.user);
          setToken(existingToken);
        }
      } catch (err) {
        // Token invalid or expired
        if (isMounted) {
          setStoredAuthToken(null);
          setToken(null);
          setUser(null);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    verifySession();

    // Listen for global 401 unauthorized events from api.js
    function handleUnauthorized() {
      logout();
    }

    window.addEventListener("cardiac-auth-unauthorized", handleUnauthorized);

    return () => {
      isMounted = false;
      window.removeEventListener("cardiac-auth-unauthorized", handleUnauthorized);
    };
  }, [logout]);

  const login = async (email, password) => {
    const data = await loginUser(email, password);
    setToken(data.access_token);
    setUser(data.user);
    return data;
  };

  const register = async (name, email, password, role = "researcher") => {
    return await registerUser(name, email, password, role);
  };

  const updateProfileState = (updatedUser) => {
    setUser(updatedUser);
  };

  const value = {
    user,
    token,
    loading,
    isAuthenticated: Boolean(token && user),
    isAdmin: user?.role === "admin",
    isReviewer: user?.role === "reviewer",
    isResearcher: user?.role === "researcher" || !user?.role,
    login,
    register,
    logout,
    updateProfileState
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

