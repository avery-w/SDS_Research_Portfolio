import { useState } from "react";
import { useNavigate } from "react-router-dom";
import client from "../api/client";

export default function Checkout() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    street: "",
    city: "",
    state: "",
    zip: "",
    country: "US",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const cartRes = await client.get("/api/cart");
      const items = cartRes.data.items.map((i: any) => ({
        product_id: i.product_id,
        quantity: i.quantity,
      }));
      await client.post("/api/orders/checkout", {
        items,
        shipping_address: form,
      });
      navigate("/orders");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Checkout failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-lg mx-auto">
      <h1 className="text-2xl font-bold mb-6">Checkout</h1>
      {error && <p className="text-red-600 mb-4">{error}</p>}
      <form onSubmit={handleSubmit} className="space-y-4">
        <input placeholder="Street" value={form.street} onChange={(e) => setForm({ ...form, street: e.target.value })} className="w-full px-3 py-2 border rounded" required />
        <input placeholder="City" value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} className="w-full px-3 py-2 border rounded" required />
        <input placeholder="State" value={form.state} onChange={(e) => setForm({ ...form, state: e.target.value })} className="w-full px-3 py-2 border rounded" required />
        <input placeholder="ZIP" value={form.zip} onChange={(e) => setForm({ ...form, zip: e.target.value })} className="w-full px-3 py-2 border rounded" required />
        <button type="submit" disabled={loading} className="w-full bg-indigo-600 text-white py-2 rounded hover:bg-indigo-700 disabled:opacity-50">
          {loading ? "Processing..." : "Place Order"}
        </button>
      </form>
    </div>
  );
}
