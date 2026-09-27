import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Trash2 } from "lucide-react";
import client from "../api/client";
import { CartItem } from "../types";

export default function Cart() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const { data: cart, isLoading } = useQuery({
    queryKey: ["cart"],
    queryFn: async () => {
      const { data } = await client.get("/api/cart");
      return data;
    },
  });

  const removeItem = useMutation({
    mutationFn: async (itemId: number) => {
      await client.delete(`/api/cart/items/${itemId}`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["cart"] }),
  });

  if (isLoading) return <p>Loading...</p>;

  const items: CartItem[] = cart?.items || [];
  const subtotal = items.reduce((sum, i) => sum + (i.product_price || 0) * i.quantity, 0);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Shopping Cart</h1>
      {items.length === 0 ? (
        <p className="text-gray-500">Your cart is empty.</p>
      ) : (
        <>
          <div className="space-y-4">
            {items.map((item) => (
              <div key={item.id} className="flex items-center justify-between bg-white p-4 rounded shadow">
                <div>
                  <p className="font-semibold">{item.product_name}</p>
                  <p className="text-sm text-gray-500">Qty: {item.quantity} × ${item.product_price?.toFixed(2)}</p>
                </div>
                <div className="flex items-center gap-4">
                  <span className="font-bold">${((item.product_price || 0) * item.quantity).toFixed(2)}</span>
                  <button onClick={() => removeItem.mutate(item.id)} className="text-red-500 hover:text-red-700">
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-6 flex justify-between items-center">
            <p className="text-xl font-bold">Subtotal: ${subtotal.toFixed(2)}</p>
            <button
              onClick={() => navigate("/checkout")}
              className="bg-indigo-600 text-white px-6 py-2 rounded-md hover:bg-indigo-700"
            >
              Proceed to Checkout
            </button>
          </div>
        </>
      )}
    </div>
  );
}
