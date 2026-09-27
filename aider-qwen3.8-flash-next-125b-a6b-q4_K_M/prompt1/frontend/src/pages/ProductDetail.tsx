import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import client from "../api/client";
import { Product } from "../types";
import { MessageCircle } from "lucide-react";

export default function ProductDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [quantity, setQuantity] = useState(1);

  const { data: product, isLoading } = useQuery({
    queryKey: ["product", id],
    queryFn: async () => {
      const { data } = await client.get(`/api/products/${id}`);
      return data as Product;
    },
  });

  const addToCart = useMutation({
    mutationFn: async () => {
      await client.post("/api/cart/items", { product_id: Number(id), quantity });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["cart"] }),
  });

  if (isLoading) return <p>Loading...</p>;
  if (!product) return <p>Product not found</p>;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
      <div>
        {product.images[0] && <img src={product.images[0]} alt={product.name} className="w-full rounded-lg" />}
      </div>
      <div>
        <h1 className="text-3xl font-bold">{product.name}</h1>
        <p className="text-2xl text-indigo-600 font-bold mt-2">${product.price.toFixed(2)}</p>
        {product.compare_at_price && (
          <p className="text-gray-400 line-through">${product.compare_at_price.toFixed(2)}</p>
        )}
        <p className="mt-4 text-gray-700">{product.description}</p>
        <p className="mt-2 text-sm text-gray-500">Stock: {product.stock_quantity}</p>
        <div className="mt-6 flex items-center gap-4">
          <input
            type="number"
            min={1}
            max={product.stock_quantity}
            value={quantity}
            onChange={(e) => setQuantity(Number(e.target.value))}
            className="w-20 px-2 py-1 border rounded"
          />
          <button
            onClick={() => addToCart.mutate()}
            disabled={addToCart.isPending}
            className="bg-indigo-600 text-white px-6 py-2 rounded-md hover:bg-indigo-700"
          >
            Add to Cart
          </button>
        </div>
        <button
          onClick={() => navigate(`/chat/${product.store_id}`)}
          className="mt-4 flex items-center gap-2 text-indigo-600 hover:underline"
        >
          <MessageCircle className="w-4 h-4" /> Message Seller
        </button>
      </div>
    </div>
  );
}
