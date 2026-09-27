import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import client from "../api/client";
import { Product } from "../types";

export default function StorePage() {
  const { id } = useParams();

  const { data: store, isLoading } = useQuery({
    queryKey: ["store", id],
    queryFn: async () => {
      const { data } = await client.get(`/api/stores/${id}`);
      return data;
    },
  });

  const { data: products = [] } = useQuery({
    queryKey: ["store-products", id],
    queryFn: async () => {
      const { data } = await client.get("/api/products", { params: { store_id: id } });
      return data as Product[];
    },
  });

  if (isLoading) return <p>Loading...</p>;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">{store?.name}</h1>
      <p className="text-gray-600 mb-6">{store?.description}</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {products.map((p) => (
          <Link key={p.id} to={`/products/${p.id}`} className="bg-white rounded-lg shadow p-4 hover:shadow-lg transition">
            {p.images[0] && <img src={p.images[0]} alt={p.name} className="w-full h-40 object-cover rounded" />}
            <h3 className="font-semibold mt-2 truncate">{p.name}</h3>
            <p className="text-indigo-600 font-bold">${p.price.toFixed(2)}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
