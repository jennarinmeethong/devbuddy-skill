#!/usr/bin/env bash
set -euo pipefail

tool_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project="$tool_root/BmsReadonlyDatabaseQuery.csproj"
release_root="$tool_root/releases"

rm -rf "$release_root"
mkdir -p "$release_root"

for rid in osx-arm64 win-x64 linux-x64; do
  output="$release_root/$rid"
  dotnet publish "$project" \
    --configuration Release \
    --runtime "$rid" \
    --self-contained true \
    --output "$output" \
    -p:PublishSingleFile=true \
    -p:IncludeNativeLibrariesForSelfExtract=true \
    -p:PublishTrimmed=false

  if [[ "$rid" == "win-x64" ]]; then
    executable="bms_readonly_database_query.exe"
  else
    executable="./bms_readonly_database_query"
    chmod +x "$output/bms_readonly_database_query"
  fi

  cp "$tool_root/appsettings.template.json" "$output/appsettings.template.json"
  sed "s|__EXECUTABLE__|$executable|g" "$tool_root/tool.json.template" > "$output/tool.json"
done

echo "Published self-contained releases under $release_root"
