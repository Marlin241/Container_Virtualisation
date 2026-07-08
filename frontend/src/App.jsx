import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import NavBar from "./components/NavBar";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import BooksPage from "./pages/BooksPage";
import LoansPage from "./pages/LoansPage";
import ProfilePage from "./pages/ProfilePage";
import UsersPage from "./pages/UsersPage";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <NavBar />
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route
            path="/books"
            element={
              <ProtectedRoute>
                <BooksPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/loans"
            element={
              <ProtectedRoute>
                <LoansPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <ProfilePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/users"
            element={
              <ProtectedRoute roles={["PERSONNEL_ADMIN"]}>
                <UsersPage />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<LoginPage />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
