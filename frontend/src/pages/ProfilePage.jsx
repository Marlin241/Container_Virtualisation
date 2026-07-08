import { useEffect, useState } from "react";
import api from "../api/client";

export default function ProfilePage() {
  const [user, setUser] = useState(null);

  useEffect(() => {
    api.get("/users/me").then((response) => setUser(response.data));
  }, []);

  if (!user) return <p>Chargement...</p>;

  return (
    <div>
      <h1>Mon profil</h1>
      <p>Nom : {user.full_name}</p>
      <p>Email : {user.email}</p>
      <p>Rôle : {user.role}</p>
    </div>
  );
}
