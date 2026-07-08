import { useEffect, useState } from "react";
import api from "../api/client";

export default function LoansPage() {
  const [loans, setLoans] = useState([]);

  async function loadLoans() {
    const response = await api.get("/loans");
    setLoans(response.data);
  }

  useEffect(() => {
    loadLoans();
  }, []);

  async function handleReturn(id) {
    await api.patch(`/loans/${id}/return`);
    loadLoans();
  }

  return (
    <div>
      <h1>Mes emprunts</h1>
      <ul>
        {loans.map((loan) => (
          <li key={loan.id}>
            Livre #{loan.book_id} — emprunté le {new Date(loan.borrowed_at).toLocaleDateString()} — statut :{" "}
            {loan.status}
            {loan.status === "EN_COURS" && <button onClick={() => handleReturn(loan.id)}>Retourner</button>}
          </li>
        ))}
      </ul>
    </div>
  );
}
