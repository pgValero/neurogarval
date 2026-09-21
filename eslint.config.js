// Configuración plana (flat config) de ESLint para los scripts del sitio.
// Solo usa reglas del núcleo de ESLint: no necesita plugins ni node_modules.
module.exports = [
  {
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "script",
      globals: {
        // Entorno de navegador
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
        // Node (para los propios archivos de configuración, eslint.config.js)
        module: "readonly",
        require: "readonly",
        process: "readonly",
        __dirname: "readonly"
      }
    },
    rules: {
      // Errores que bloquean el commit
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
      // Avisos (no bloquean el commit)
      "no-unused-vars": ["warn", { "args": "none" }],
      "no-empty": ["warn", { "allowEmptyCatch": true }]
    }
  }
];
