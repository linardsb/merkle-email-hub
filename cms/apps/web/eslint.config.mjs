import { FlatCompat } from "@eslint/eslintrc";
import nextPlugin from "@next/eslint-plugin-next";
import jsxA11y from "eslint-plugin-jsx-a11y";
import security from "eslint-plugin-security";
import reactHooks from "eslint-plugin-react-hooks";
import prettier from "eslint-config-prettier";

const compat = new FlatCompat({ baseDirectory: import.meta.dirname });

/** @type {import("eslint").Linter.Config[]} */
export default [
  // === Ignores ===
  {
    ignores: [
      ".next/**",
      "node_modules/**",
      "dist/**",
      "coverage/**",
      "playwright-report/**",
      "e2e/**/*.ts",
    ],
  },

  // === Next.js core rules ===
  ...compat.extends("next/core-web-vitals"),

  // === Security plugin ===
  security.configs.recommended,

  // === JSX Accessibility (strict) ===
  jsxA11y.flatConfigs.strict,

  // === React Hooks ===
  {
    plugins: { "react-hooks": reactHooks },
    rules: {
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
    },
  },

  // === Next.js plugin (explicit) ===
  {
    plugins: { "@next/next": nextPlugin },
    rules: {
      ...nextPlugin.configs.recommended.rules,
      ...nextPlugin.configs["core-web-vitals"].rules,
    },
  },

  // === Project-specific rules ===
  {
    rules: {
      // Security hardening
      "no-eval": "error",
      "no-implied-eval": "error",
      "no-new-func": "error",
      "no-script-url": "error",
      "security/detect-object-injection": "off", // Too noisy for TS

      // Code quality
      "no-console": ["warn", { allow: ["warn", "error"] }],
      "no-debugger": "error",
      "no-alert": "error",
      "prefer-const": "error",
      "no-var": "error",
      "eqeqeq": ["error", "always"],
      "no-implicit-coercion": "error",
      "curly": ["error", "all"],

      // Import hygiene
      "no-duplicate-imports": "error",

      // Enforce POLL.* constants for refreshInterval (Phase 42.7)
      "no-restricted-syntax": [
        "error",
        {
          selector:
            "Property[key.name='refreshInterval'][value.type='Literal'][value.value!=0]",
          message:
            "Use POLL.* constants from @/lib/swr-constants instead of hardcoded refreshInterval values.",
        },
      ],

      // React best practices
      "react/no-danger": "warn",
      "react/self-closing-comp": "error",

      // Accessibility
      "jsx-a11y/anchor-is-valid": "error",
      "jsx-a11y/click-events-have-key-events": "error",
      "jsx-a11y/no-autofocus": "warn",
    },
  },

  // === Test file relaxations ===
  {
    files: ["**/*.test.ts", "**/*.test.tsx", "**/__tests__/**"],
    rules: {
      "no-console": "off",
      "security/detect-non-literal-fs-filename": "off",
      "no-restricted-syntax": "off",
    },
  },

  // === Prettier must be last (disables conflicting format rules) ===
  prettier,
];
