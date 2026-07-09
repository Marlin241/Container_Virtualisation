import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";

export default function RegisterPage() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("ETUDIANT");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      await api.post("/auth/register", { full_name: fullName, email, password, role });
      navigate("/login");
    } catch (err) {
      setError("Impossible de créer le compte (email déjà utilisé ?)");
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <h1>Inscription</h1>
      {error && <p style={{ color: "red" }}>{error}</p>}
      <input placeholder="Nom complet" value={fullName} onChange={(e) => setFullName(e.target.value)} required />
      <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
      <input
        type="password"
        placeholder="Mot de passe"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />
      <select value={role} onChange={(e) => setRole(e.target.value)}>
        <option value="ETUDIANT">Étudiant</option>
        <option value="PROFESSEUR">Professeur</option>
      </select>
      <button type="submit">Créer le compte</button>
    </form>
  );
}
