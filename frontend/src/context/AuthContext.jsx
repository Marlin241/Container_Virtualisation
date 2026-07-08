import { createContext, useContext, useState } from "react";
import api from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [role, setRole] = useState(localStorage.getItem("role"));

  async function login(email, password) {
    const response = await api.post("/auth/login", { email, password });
    const accessToken = response.data.access_token;
    localStorage.setItem("token", accessToken);
    setToken(accessToken);

    const me = await api.get("/users/me", {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    localStorage.setItem("role", me.data.role);
    setRole(me.data.role);
  }

  function logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("role");
    setToken(null);
    setRole(null);
  }

  return (
    <AuthContext.Provider value={{ token, role, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
