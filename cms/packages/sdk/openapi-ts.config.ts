import { defineConfig } from "@hey-api/openapi-ts";

export default defineConfig({
  client: "@hey-api/client-fetch",
  input: "http://localhost:8891/openapi.json",
  output: {
    format: "prettier",
    path: "src/client",
  },
});
