import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import client from "../api/client";
import { Order } from "../types";

export default function Orders() {
  const { data: orders = [], isLoading } = useQuery({
    queryKey: ["orders"],
    queryFn: async () => {
      const { data } = await client.get("/api/orders/my");
      return data as Order[];
    },
  });

  if (isLoading) return <p>Loading...</p>;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">My Orders</h1>
      {orders.length === 0 ? (
        <p className="text-gray-500">No orders yet.</p>
      ) : (
        <div className="space-y-4">
          {orders.map((order) => (
            <div key={order.id} className="bg-white p-4 rounded shadow">
              <div className="flex justify-between">
                <span className="font-mono text-sm">{order.order_number}</span>
                <span className="text-sm text-gray-500">{new Date(order.created_at).toLocaleDateString()}</span>
              </div>
              <p className="mt-2 font-bold">${order.total.toFixed(2)}</p>
              <p className="text-sm text-gray-600">Status: <span className="capitalize">{order.status}</span></p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
