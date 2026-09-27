import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import client from "../api/client";

export default function SellerDashboard() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({ name: "", price: "", stock_quantity: "0", category: "", description: "" });

  const { data: products = [] } = useQuery({
    queryKey: ["seller-products"],
    queryFn: async () => {
      const { data } = await client.get("/api/products");
      return data;
    },
  });

  const createProduct = useMutation({
    mutationFn: async () => {
      await client.post("/api/products", {
        ...form,
        price: Number(form.price),
        stock_quantity: Number(form.stock_quantity),
      });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["seller-products"] }),
  });

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Seller Dashboard</h1>
      <div className="bg-white p-6 rounded shadow mb-6">
        <h2 className="text-lg font-semibold mb-4">Add Product</h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createProduct.mutate();
          }}
          className="grid grid-cols-1 md:grid-cols-2 gap-4"
        >
          <input placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="px-3 py-2 border rounded" required />
          <input placeholder="Price" type="number" step="0.01" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} className="px-3 py-2 border rounded" required />
          <input placeholder="Stock" type="number" value={form.stock_quantity} onChange={(e) => setForm({ ...form, stock_quantity: e.target.value })} className="px-3 py-2 border rounded" />
          <input placeholder="Category" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className="px-3 py-2 border rounded" />
          <textarea placeholder="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="px-3 py-2 border rounded md:col-span-2" />
          <button type="submit" className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700">
            Add Product
          </button>
        </form>
      </div>
      <h2 className="text-lg font-semibold mb-4">My Products</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {products.map((p: any) => (
          <div key={p.id} className="bg-white p-4 rounded shadow">
            <p className="font-semibold">{p.name}</p>
            <p className="text-indigo-600">${p.price?.toFixed(2)}</p>
            <p className="text-sm text-gray-500">Stock: {p.stock_quantity}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
