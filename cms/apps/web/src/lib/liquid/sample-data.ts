/**
 * Sample subscriber/product data for Liquid preview rendering.
 */
export const SAMPLE_DATA: Record<string, unknown> = {
  subscriber: {
    first_name: "Alex",
    last_name: "Johnson",
    email: "alex.johnson@example.com",
    city: "San Francisco",
    country: "US",
    tier: "gold",
  },
  products: [
    { name: "Running Shoes", price: "$129.99", image_url: "https://picsum.photos/seed/shoes/200/200" },
    { name: "Training T-Shirt", price: "$49.99", image_url: "https://picsum.photos/seed/shirt/200/200" },
    { name: "Water Bottle", price: "$24.99", image_url: "https://picsum.photos/seed/bottle/200/200" },
  ],
  company: {
    name: "Acme Inc.",
    website: "https://www.example.com",
    logo_url: "https://picsum.photos/seed/logo/150/50",
  },
  unsubscribe_url: "https://example.com/unsubscribe?token=abc123",
  current_year: new Date().getFullYear(),
  is_member: true,
};
