import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import client from "../api/client";
import { Product } from "../types";

export default function Products() {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [page, setPage] = useState(1);

  const { data: products = [], isLoading } = useQuery({
    queryKey: ["products", search, category, page],
    queryFn: async () => {
      const params: Record<string, string | number> = { page, per_page: 20 };
      if (search) params.search = search;
      if (category) params.category = category;
      const { data } = await client.get("/api/products", { params });
      return data as Product[];
    },
  });

  return (
    <div>
      <div className="flex gap-4 mb-6">
        <input
          type="text"
          placeholder="Search products..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 px-3 py-2 border rounded-md"
        />
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="px-3 py-2 border rounded-md"
        >
          <option value="">All Categories</option>
          <option value="electronics">Electronics</option>
          <option value="clothing">Clothing</option>
          <option value="home">Home</option>
        </select>
      </div>

      {isLoading ? (
        <p>Loading...</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {products.map((p) => (
            <Link key={p.id} to={`/products/${p.id}`} className="bg-white rounded-lg shadow hover:shadow-lg transition p-4">
              {p.images[0] && <img src={p.images[0]} alt={p.name} className="w-full h-48 object-cover rounded" />}
              <h3 className="font-semibold mt-2 truncate">{p.name}</h3>
              <p className="text-indigo-600 font-bold">${p.price.toFixed(2)}</p>
              <p className="text-xs text-gray-500">Stock: {p.stock_quantity}</p>
            </Link>
          ))}
        </div>
      )}

      <div className="flex justify-center mt-6 gap-2">
        <button onClick={() => setPage((p) => Math.max(1, p - 1))} className="px-3 py-1 border rounded">Prev</button>
        <span className="px-3 py-1">Page {page}</span>
        <button onClick={() => setPage((p) => p + 1)} className="px-3 py-1 border rounded">Next</button>
      </div>
    </div>
  );
}
