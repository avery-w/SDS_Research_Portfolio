import { useQuery } from "@tanstack/react-query";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import client from "../api/client";

export default function AdminDashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ["admin-analytics"],
    queryFn: async () => {
      const { data } = await client.get("/api/admin/analytics/sales");
      return data;
    },
  });

  if (isLoading) return <p>Loading...</p>;

  const chartData = (data?.top_products || []).map((p: any) => ({
    name: p.name,
    revenue: p.total_revenue,
    sold: p.total_sold,
  }));

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Admin Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white p-6 rounded shadow">
          <p className="text-sm text-gray-500">Total Orders</p>
          <p className="text-3xl font-bold">{data?.summary?.total_orders || 0}</p>
        </div>
        <div className="bg-white p-6 rounded shadow">
          <p className="text-sm text-gray-500">Total Revenue</p>
          <p className="text-3xl font-bold">${(data?.summary?.total_revenue || 0).toFixed(2)}</p>
        </div>
        <div className="bg-white p-6 rounded shadow">
          <p className="text-sm text-gray-500">Avg Order Value</p>
          <p className="text-3xl font-bold">${(data?.summary?.avg_order_value || 0).toFixed(2)}</p>
        </div>
      </div>
      <div className="bg-white p-6 rounded shadow">
        <h2 className="text-lg font-semibold mb-4">Top Products by Revenue</h2>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="revenue" fill="#4f46e5" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
