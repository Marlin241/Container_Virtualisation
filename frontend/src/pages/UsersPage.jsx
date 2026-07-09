import { useEffect, useState } from "react";
import api from "../api/client";

export default function UsersPage() {
  const [users, setUsers] = useState([]);
  const [error, setError] = useState("");

  async function loadUsers() {
    const response = await api.get("/users");
    setUsers(response.data);
  }

  useEffect(() => {
    loadUsers();
  }, []);

  async function handlePromote(id) {
    setError("");
    try {
      await api.patch(`/users/${id}/promote`);
      loadUsers();
    } catch (err) {
      setError("Promotion impossible");
    }
  }

  return (
    <div>
      <h1>Utilisateurs</h1>
      {error && <p style={{ color: "red" }}>{error}</p>}
      <ul>
        {users.map((user) => (
          <li key={user.id}>
            {user.full_name} — {user.email} — {user.role}
            {user.role !== "PERSONNEL_ADMIN" && (
              <button onClick={() => handlePromote(user.id)}>Promouvoir en admin</button>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
