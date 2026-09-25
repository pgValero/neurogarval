#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/.." && pwd)"
site_domain="$(< "$repo_root/src/CNAME")"
if [[ ! "$site_domain" =~ ^[A-Za-z0-9.-]+$ ]]; then
  echo "::error::src/CNAME no contiene un dominio válido"
  exit 1
fi

site_url="https://$site_domain"
curl_options=(
  --fail-with-body
  --silent
  --show-error
  --location
  --retry 2
  --retry-delay 5
  --connect-timeout 10
  --max-time 30
)

check_url() {
  local url="$1"
  local body

  if ! body="$(curl "${curl_options[@]}" "$url")"; then
    echo "::error::No se pudo acceder a $url"
    return 1
  fi

  if [[ -z "$body" ]]; then
    echo "::error::La respuesta de $url está vacía"
    return 1
  fi
}

if ! homepage="$(curl "${curl_options[@]}" "$site_url/")"; then
  echo "::error::No se pudo acceder a $site_url/"
  exit 1
fi

if [[ -z "$homepage" ]]; then
  echo "::error::La portada está vacía"
  exit 1
fi

if [[ "$homepage" =~ __[a-zA-Z0-9_.]+__ ]]; then
  echo "::error::La portada contiene marcadores de plantilla sin resolver"
  exit 1
fi

if [[ "$homepage" != *"<title>"* || "$homepage" != *"</title>"* ]]; then
  echo "::error::La portada no contiene un título HTML válido"
  exit 1
fi

if [[ "$homepage" != *"$site_url"* ]]; then
  echo "::error::La portada no contiene la URL canónica esperada"
  exit 1
fi

if ! grep -Eq '<(h1|p|li)([[:space:]][^>]*)?>[[:space:]]*[^<[:space:]]' <<< "$homepage"; then
  echo "::error::La portada no contiene texto visible"
  exit 1
fi

if ! grep -Eq '<img[[:space:]][^>]*src="[^"]+"' <<< "$homepage"; then
  echo "::error::La portada no contiene una imagen con URL"
  exit 1
fi

if ! grep -Eq '(href|src)="https?://[^"]+"' <<< "$homepage"; then
  echo "::error::La portada no contiene una URL absoluta"
  exit 1
fi

check_url "$site_url/robots.txt"
check_url "$site_url/sitemap.xml"
check_url "$site_url/llms.txt"
check_url "$site_url/llms-full.txt"
check_url "$site_url/logo.svg"
check_url "$site_url/favicon.svg"

echo "::notice::Sitio accesible correctamente en $site_url/"
