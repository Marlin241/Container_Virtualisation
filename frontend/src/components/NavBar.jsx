import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function NavBar() {
  const { token, role, logout } = useAuth();

  return (
    <nav>
      <Link to="/books">Livres</Link>
      {token && <Link to="/loans">Mes emprunts</Link>}
      {role === "PERSONNEL_ADMIN" && <Link to="/users">Utilisateurs</Link>}
      {token && <Link to="/profile">Profil</Link>}
      {!token && <Link to="/login">Connexion</Link>}
      {!token && <Link to="/register">Inscription</Link>}
      {token && <button onClick={logout}>Déconnexion</button>}
    </nav>
  );
}
