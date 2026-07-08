import { useEffect, useState } from "react";
import api from "../api/client";

export default function UsersPage() {
  const [users, setUsers] = useState([]);

  useEffect(() => {
    api.get("/users").then((response) => setUsers(response.data));
  }, []);

  return (
    <div>
      <h1>Utilisateurs</h1>
      <ul>
        {users.map((user) => (
          <li key={user.id}>
            {user.full_name} — {user.email} — {user.role}
          </li>
        ))}
      </ul>
    </div>
  );
}
