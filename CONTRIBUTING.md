# Contribución

## Construir el proyecto

El sitio se genera con el script `scripts/build.py`. Ejecuta estos comandos desde la raíz del repositorio:

```bash
python -m pip install pyyaml markdown pillow
python scripts/build.py
```

El sitio generado se encuentra en `_site/`. Para verlo, abre `_site/index.html` en el navegador; no abras `src/index.html` directamente, porque todavía contiene los marcadores y los datos de contacto pendientes de resolver.

Si prefieres usar [`uv`](https://docs.astral.sh/uv/), puedes ejecutar el build sin instalar las dependencias permanentemente:

```bash
uv run --with pyyaml --with markdown --with pillow python scripts/build.py
```

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
