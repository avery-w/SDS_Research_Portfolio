export interface User {
  id: number;
  email: string;
  full_name: string;
  phone: string | null;
  role: "customer" | "seller" | "admin";
  is_active: boolean;
  is_verified: boolean;
  avatar_url: string | null;
  created_at: string;
}

export interface Product {
  id: number;
  name: string;
  slug: string | null;
  description: string | null;
  price: number;
  compare_at_price: number | null;
  sku: string | null;
  barcode: string | null;
  category: string | null;
  tags: string[];
  images: string[];
  stock_quantity: number;
  weight_oz: number | null;
  dimensions: Record<string, number> | null;
  is_active: boolean;
  store_id: number;
  created_at: string;
  updated_at: string;
}

export interface Order {
  id: number;
  order_number: string;
  status: string;
  subtotal: number;
  shipping_cost: number;
  tax: number;
  total: number;
  shipping_address: Record<string, string>;
  billing_address: Record<string, string> | null;
  tracking_number: string | null;
  carrier: string | null;
  cancellation_reason: string | null;
  return_reason: string | null;
  customer_id: number;
  created_at: string;
  updated_at: string;
  items: OrderItem[];
}

export interface OrderItem {
  id: number;
  product_id: number;
  quantity: number;
  unit_price: number;
  total_price: number;
}

export interface Store {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  logo_url: string | null;
  banner_url: string | null;
  is_active: boolean;
  rating: number;
  total_reviews: number;
  owner_id: number;
  created_at: string;
  updated_at: string;
}

export interface CartItem {
  id: number;
  product_id: number;
  quantity: number;
  product_name: string | null;
  product_price: number | null;
  product_image: string | null;
}

export interface ChatMessage {
  id: number;
  session_id: number;
  sender_id: number;
  content: string;
  is_ai_generated: boolean;
  created_at: string;
}
