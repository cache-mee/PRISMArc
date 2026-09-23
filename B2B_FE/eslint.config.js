// ESLint flat config (eslint.config.js).
//
// Config style: flat config is used because ESLint 10.x (installed here) no
// longer supports the legacy `.eslintrc.*` format at all — flat config is the
// only option, not a stylistic choice.
//
// Rule sets, per stack/rules/base-rules.md -> Language & Style (Frontend):
// "eslint with the standard @typescript-eslint/recommended + eslint-plugin-react-hooks
// rule sets. Do not hand-roll a custom rule set for this build."
//   - `typescript-eslint` (the official meta-package maintained by the
//     @typescript-eslint team) exposes `tseslint.configs.recommended`, which is
//     the same "recommended" rule set as `@typescript-eslint/recommended`,
//     packaged for flat config consumption.
//   - `eslint-plugin-react-hooks`'s official flat-config recommended preset
//     (`reactHooks.configs.flat.recommended`) is used as-is.
//   - `@eslint/js`'s `recommended` config supplies the base JS rule set that
//     `@typescript-eslint/recommended` itself builds on top of.
// No custom/hand-tuned rules are added on top of these presets.
import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  {
    ignores: ["dist/**", "node_modules/**"],
  },
  {
    files: ["**/*.{ts,tsx}"],
    extends: [
      js.configs.recommended,
      ...tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
    ],
    languageOptions: {
      ecmaVersion: 2023,
      globals: globals.browser,
    },
  },
);
