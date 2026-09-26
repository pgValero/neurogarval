// ESLint flat config for the site scripts.
// It only uses ESLint core rules: no plugins or node_modules needed.
module.exports = [
  {
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "script",
      globals: {
        // Browser environment
        window: "readonly",
        document: "readonly",
        navigator: "readonly",
        location: "readonly",
        history: "readonly",
        console: "readonly",
        fetch: "readonly",
        URL: "readonly",
        URLSearchParams: "readonly",
        FormData: "readonly",
        localStorage: "readonly",
        sessionStorage: "readonly",
        setTimeout: "readonly",
        clearTimeout: "readonly",
        setInterval: "readonly",
        clearInterval: "readonly",
        requestAnimationFrame: "readonly",
        cancelAnimationFrame: "readonly",
        getComputedStyle: "readonly",
        matchMedia: "readonly",
        alert: "readonly",
        confirm: "readonly",
        prompt: "readonly",
        event: "readonly",
        // Node (for the config files themselves, eslint.config.js)
        module: "readonly",
        require: "readonly",
        process: "readonly",
        __dirname: "readonly"
      }
    },
    rules: {
      // Errors that block the commit
      "no-undef": "error",
      "no-dupe-keys": "error",
      "no-dupe-args": "error",
      "no-dupe-class-members": "error",
      "no-dupe-else-if": "error",
      "no-func-assign": "error",
      "no-import-assign": "error",
      "no-obj-calls": "error",
      "no-self-assign": "error",
      "no-self-compare": "error",
      "no-sparse-arrays": "error",
      "no-unreachable": "error",
      "no-unsafe-negation": "error",
      "no-unsafe-optional-chaining": "error",
      "no-unsafe-finally": "error",
      "no-constant-binary-expression": "error",
      "no-setter-return": "error",
      "no-prototype-builtins": "error",
      "use-isnan": "error",
      "valid-typeof": "error",
      // Warnings (do not block the commit)
      "no-unused-vars": ["warn", { "args": "none" }],
      "no-empty": ["warn", { "allowEmptyCatch": true }]
    }
  }
];
