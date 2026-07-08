import { useEffect, useState } from "react";
import api from "../api/client";
import { useAuth } from "../context/AuthContext";

const emptyForm = { title: "", author: "", isbn: "", total_copies: 1 };

export default function BooksPage() {
  const { role } = useAuth();
  const [books, setBooks] = useState([]);
  const [search, setSearch] = useState("");
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState("");

  async function loadBooks(query = "") {
    const url = query ? `/books/search?title=${encodeURIComponent(query)}` : "/books";
    const response = await api.get(url);
    setBooks(response.data);
  }

  useEffect(() => {
    loadBooks();
  }, []);

  async function handleSearch(e) {
    e.preventDefault();
    loadBooks(search);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      if (editingId) {
        await api.put(`/books/${editingId}`, form);
      } else {
        await api.post("/books", form);
      }
      setForm(emptyForm);
      setEditingId(null);
      loadBooks();
    } catch (err) {
      setError("Opération impossible (ISBN déjà utilisé ?)");
    }
  }

  function startEdit(book) {
    setEditingId(book.id);
    setForm({ title: book.title, author: book.author, isbn: book.isbn, total_copies: book.total_copies });
  }

  async function handleDelete(id) {
    await api.delete(`/books/${id}`);
    loadBooks();
  }

  async function handleBorrow(id) {
    setError("");
    try {
      await api.post("/loans", { book_id: id });
      loadBooks();
    } catch (err) {
      setError("Emprunt impossible (livre indisponible ?)");
    }
  }

  return (
    <div>
      <h1>Livres</h1>
      {error && <p style={{ color: "red" }}>{error}</p>}
      <form onSubmit={handleSearch}>
        <input placeholder="Rechercher par titre" value={search} onChange={(e) => setSearch(e.target.value)} />
        <button type="submit">Rechercher</button>
      </form>

      {role === "PERSONNEL_ADMIN" && (
        <form onSubmit={handleSubmit}>
          <h2>{editingId ? "Modifier le livre" : "Ajouter un livre"}</h2>
          <input
            placeholder="Titre"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            required
          />
          <input
            placeholder="Auteur"
            value={form.author}
            onChange={(e) => setForm({ ...form, author: e.target.value })}
            required
          />
          <input
            placeholder="ISBN"
            value={form.isbn}
            onChange={(e) => setForm({ ...form, isbn: e.target.value })}
            required
          />
          <input
            type="number"
            min="1"
            value={form.total_copies}
            onChange={(e) => setForm({ ...form, total_copies: Number(e.target.value) })}
            required
          />
          <button type="submit">{editingId ? "Enregistrer" : "Ajouter"}</button>
        </form>
      )}

      <ul>
        {books.map((book) => (
          <li key={book.id}>
            <strong>{book.title}</strong> — {book.author} ({book.isbn}) — {book.available_copies}/
            {book.total_copies} dispo
            <button onClick={() => handleBorrow(book.id)} disabled={book.available_copies < 1}>
              Emprunter
            </button>
            {role === "PERSONNEL_ADMIN" && (
              <>
                <button onClick={() => startEdit(book)}>Modifier</button>
                <button onClick={() => handleDelete(book.id)}>Supprimer</button>
              </>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
