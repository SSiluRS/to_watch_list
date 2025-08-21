param (
  [Parameter(Mandatory = $true)]
  [string]$Version
)

function Fail($msg) { Write-Error $msg; exit 1 }

# 1) Проверка версии X.Y.Z
if ($Version -notmatch '^\d+\.\d+\.\d+$') { Fail "Версия должна быть в формате X.Y.Z (например, 1.2.3)" }

# 2) Проверка git чистоты и ветки
$branch = (git rev-parse --abbrev-ref HEAD) 2>$null
if (-not $branch) { Fail "Git недоступен в PATH" }
if ($branch -ne "main") { Write-Warning "Сейчас ветка: $branch (не main). Продолжаю..." }

$dirty = git status --porcelain
if ($dirty) { Fail "Рабочее дерево не чистое. Закоммить изменения и повтори." }

# 3) Тег уже существует?
$tagExists = git rev-parse "v$Version" 2>$null
if ($LASTEXITCODE -eq 0) { Fail "Тег v$Version уже существует" }

# 4) Обновить VERSION
Set-Content -Path "VERSION" -Value $Version -NoNewline
Write-Host "✔ VERSION -> $Version"

# 5) Обновить версию во фронте (frontend/package.json)
$pkgPath = "frontend/package.json"
if (Test-Path $pkgPath) {
  $json = Get-Content $pkgPath -Raw | ConvertFrom-Json
  $json.version = $Version
  $json | ConvertTo-Json -Depth 20 | Out-File $pkgPath -Encoding UTF8
  Write-Host "✔ $pkgPath -> version = $Version"
} else {
  Write-Warning "frontend/package.json не найден — пропускаю"
}

# 6) Коммит + тег
git add -A
git commit -m "chore: release v$Version" | Out-Null
git tag -a "v$Version" -m "Release v$Version"
Write-Host "✔ Создан коммит и тег v$Version"

# 7) Push
git push origin $branch
git push origin "v$Version"
Write-Host "🚀 Отправлено в origin ($branch + тег v$Version). Дальше CI соберёт образы в GHCR."
