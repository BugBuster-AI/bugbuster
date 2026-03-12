import tsParser from "@typescript-eslint/parser";
import reactPlugin from "eslint-plugin-react";
import reactHooksPlugin from "eslint-plugin-react-hooks";
import reactRefreshPlugin from "eslint-plugin-react-refresh";
import importPlugin from "eslint-plugin-import";
import lodashPlugin from "eslint-plugin-lodash";
import typescriptPlugin from "@typescript-eslint/eslint-plugin";

export default [
    {
        files: ["**/*.ts", "**/*.tsx"],
        ignores: ["dist/**", "node_modules/**", "vite.config.ts", "**/*.d.ts"],
        languageOptions: {
            ecmaVersion: 2020,
            sourceType: "module",
            parser: tsParser,
            parserOptions: {
                project: ["./tsconfig.json", "./tsconfig.node.json"], // Указываем оба конфига
                tsconfigRootDir: import.meta.dirname,
                ecmaFeatures: {
                    jsx: true,
                },
            },
        },
        settings: {
            react: {
                version: "detect",
            },
        },
        plugins: {
            "@typescript-eslint": typescriptPlugin,
            import: importPlugin,
            lodash: lodashPlugin,
            react: reactPlugin,
            "react-hooks": reactHooksPlugin,
            "react-refresh": reactRefreshPlugin,
        },
        rules: {
            // Правила ESLint
            "linebreak-style": [2, "unix"],
            indent: [2, 4, {SwitchCase: 1}], // Стандартное правило `indent`
            "object-curly-spacing": [2, "always"],
            "@typescript-eslint/object-curly-spacing": "off",
            "space-before-function-paren": [2, "always"],
            quotes: [2, "single", {allowTemplateLiterals: true}],
            "jsx-quotes": [2, "prefer-double"],
            "max-len": ["error", {code: 120, tabWidth: 4}],
            "max-lines": [2, 700],
            "no-console": [2, {allow: ["error"]}],
            "no-unused-vars": 0,
            "eol-last": [2, "always"],
            "no-confusing-arrow": 2,
            "arrow-parens": [2, "always"],
            "no-param-reassign": 2,
            "prefer-template": 0,
            "no-script-url": 2,
            "prefer-promise-reject-errors": 0,
            "padding-line-between-statements": [
                2,
                {blankLine: "always", prev: "import", next: "*"},
                {blankLine: "any", prev: "import", next: "import"},
                {blankLine: "always", prev: "*", next: "return"},
                {blankLine: "always", prev: ["const", "let", "var"], next: "*"},
                {
                    blankLine: "any",
                    prev: ["const", "let", "var"],
                    next: ["const", "let", "var"],
                },
            ],
            "multiline-comment-style": [2, "starred-block"],
            "default-case": 0,
            "prefer-destructuring": 0,
            "rest-spread-spacing": [2, "never"],
            "array-bracket-newline": [2, "consistent"],
            "no-unused-expressions": 0,
            "class-methods-use-this": 0,
            "no-plusplus": 0,
            "global-require": 0,
            "no-useless-constructor": 0,
            "no-empty-function": 0,
            camelcase: "off",
            "lines-between-class-members": [
                "error",
                "always",
                {exceptAfterSingleLine: false},
            ],
            "import/no-useless-path-segments": [2, {noUselessIndex: true}],
            "import/first": 2,
            "import/newline-after-import": 2,
            "import/no-duplicates": 2,
            "import/no-unresolved": 0,
            "import/order": [
                "error",
                {
                    groups: ["builtin", "external", "internal"],
                    alphabetize: {order: "asc", caseInsensitive: true},
                    "newlines-between": "never",
                },
            ],
            "lodash/import-scope": [2, "method"],
            "lodash/prop-shorthand": 0,
            "lodash/matches-shorthand": 0,
            "lodash/matches-prop-shorthand": 0,
            "@typescript-eslint/explicit-function-return-type": 0,
            "@typescript-eslint/no-empty-function": 2,
            "@typescript-eslint/no-namespace": 0,
            "@typescript-eslint/no-unused-vars": [
                2,
                {
                    vars: "all",
                    args: "after-used",
                    ignoreRestSiblings: true,
                },
            ],
            "@typescript-eslint/no-use-before-define": 2,
            "@typescript-eslint/naming-convention": [
                "error",
                {
                    selector: "enum",
                    format: ["PascalCase"],
                    prefix: ["E"],
                },
            ],
            "@typescript-eslint/no-var-requires": 0,
            "@typescript-eslint/consistent-type-definitions": [2, "interface"],
            "@typescript-eslint/no-explicit-any": 1,
            "react/no-adjacent-inline-elements": 2,
            "react/no-array-index-key": 0,
            "react/no-danger": 0,
            "react/no-direct-mutation-state": 2,
            "react/prefer-stateless-function": 2,
            "react/require-default-props": 0,
            "react/react-in-jsx-scope": 0,
            "react/display-name": 0,
            "react/jsx-curly-newline": 0,
            "react/jsx-curly-spacing": [2, "always"],
            "react/jsx-filename-extension": [2, {extensions: [".jsx", ".tsx"]}],
            "react/jsx-first-prop-new-line": [2, "multiline"],
            "react/jsx-handler-names": 2,
            "react/jsx-indent": [2, 4],
            "react/jsx-indent-props": [2, 4],
            "react/jsx-key": 2,
            "react/jsx-max-depth": [2, {max: 10}],
            "react/jsx-newline": 0,
            "react/jsx-no-bind": 0,
            "react/jsx-no-constructed-context-values": 2,
            "react/jsx-max-props-per-line": [
                "error",
                {maximum: 1, when: "multiline"},
            ],
            "react/jsx-no-script-url": 2,
            "react/jsx-no-target-blank": 0,
            "react/jsx-no-useless-fragment": 2,
            "react/jsx-props-no-spreading": 0,
            "react/jsx-sort-props": [
                2,
                {ignoreCase: true, shorthandLast: true, reservedFirst: true},
            ],
            "react-hooks/exhaustive-deps": 0,
            "no-multi-str": 2,
        },
    },
];
