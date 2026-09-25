# Contribución

## Hook de pre-commit

La configuración de los hooks está en `.pre-commit/`. Instala el hook desde la raíz del repositorio con:

```bash
prek install --config .pre-commit/.pre-commit-config.yaml --force
```

A partir de entonces, `prek` se ejecutará automáticamente en cada `git commit`.

Para ejecutar todos los hooks manualmente:

```bash
prek run --config .pre-commit/.pre-commit-config.yaml --all-files
```
