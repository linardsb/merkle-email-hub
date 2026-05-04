import nextPlugin from "@next/eslint-plugin-next";
import jsxA11y from "eslint-plugin-jsx-a11y";
import security from "eslint-plugin-security";
import react from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";
import prettier from "eslint-config-prettier";
import tseslint from "typescript-eslint";

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

  // === TypeScript parser/rules (applies to .ts/.tsx) ===
  ...tseslint.configs.recommended,

  // === Security plugin ===
  security.configs.recommended,

  // === JSX Accessibility (strict) ===
  jsxA11y.flatConfigs.strict,

  // === React + React Hooks ===
  {
    plugins: { react, "react-hooks": reactHooks },
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
      // eslint-plugin-security@3.0.1 ships an Express-only rule that calls
      // context.getSourceCode(), removed in ESLint 10. Disable until upstream
      // fix lands (https://github.com/eslint-community/eslint-plugin-security).
      "security/detect-no-csrf-before-method-override": "off",

      // Code quality
      "no-console": ["warn", { allow: ["warn", "error"] }],
      "no-debugger": "error",
      "no-alert": "error",
      "prefer-const": "error",
      "no-var": "error",
      eqeqeq: ["error", "always", { null: "ignore" }],
      "no-implicit-coercion": "error",
      curly: ["error", "all"],

      // Underscore-prefix opt-out for unused vars/args
      "@typescript-eslint/no-unused-vars": [
        "error",
        {
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
          caughtErrorsIgnorePattern: "^_",
          destructuredArrayIgnorePattern: "^_",
        },
      ],

      // Import hygiene — allow `import type { X }` alongside `import { Y }` from same module
      "no-duplicate-imports": ["error", { allowSeparateTypeImports: true }],

      // Enforce POLL.* constants for refreshInterval (Phase 42.7)
      "no-restricted-syntax": [
        "error",
        {
          selector: "Property[key.name='refreshInterval'][value.type='Literal'][value.value!=0]",
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

  // === Build scripts (Node, not runtime) ===
  // Filesystem access and console output are inherent to build tooling.
  {
    files: ["scripts/**/*.{mjs,js,ts}"],
    rules: {
      "security/detect-non-literal-fs-filename": "off",
      "security/detect-unsafe-regex": "off",
      "no-console": "off",
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

  // === Tracked debt (see docs/eslint-debt.md) ===
  // These rules are demoted to allow Phase 1b to remove `|| true` wrappers from
  // CI/pre-commit. Each demotion has an entry in docs/eslint-debt.md with the
  // ratchet target. Re-promote one rule at a time as backlog is paid down.
  {
    rules: {
      // 19 sites — fix or underscore-prefix per file
      "@typescript-eslint/no-unused-vars": "off",
      // 15 sites — migrate to next/image where viable
      "@next/next/no-img-element": "off",
      // 12 sites — many are valid intentional omissions; review per case
      "react-hooks/exhaustive-deps": "off",
      // 12 sites — review @ts-* comments and add justifications
      "@typescript-eslint/ban-ts-comment": "off",
      // 26 sites across multiple a11y rules — accessibility audit follow-up
      "jsx-a11y/label-has-associated-control": "off",
      "jsx-a11y/click-events-have-key-events": "off",
      "jsx-a11y/no-static-element-interactions": "off",
      "jsx-a11y/no-noninteractive-element-interactions": "off",
      "jsx-a11y/no-noninteractive-tabindex": "off",
      "jsx-a11y/role-supports-aria-props": "off",
      "jsx-a11y/media-has-caption": "off",
      // 7 + 3 sites — review regex inputs for taint
      "security/detect-non-literal-regexp": "off",
      "security/detect-unsafe-regex": "off",
      // 2 sites — DOMPurify-sanitized HTML; track and audit
      "react/no-danger": "off",
      // 2 sites — modal-focus UX; replace with imperative ref-based focus
      "jsx-a11y/no-autofocus": "off",
    },
  },

  // === Prettier must be last (disables conflicting format rules) ===
  prettier,
];
