param(
  [Parameter(Mandatory = $true)]
  [ValidateSet("back","front","both")]
  [string]$Service,

  [Parameter(Mandatory = $true)]
  [string]$Version,

  [switch]$NoPush,
  [switch]$NoCommit
)

function Fail($msg) { Write-Error $msg; exit 1 }

Write-Host "== ToWatchList release =="
Write-Host " Service: $Service"
Write-Host " Version: $Version"

# 1) SemVer X.Y.Z
if ($Version -notmatch '^\d+\.\d+\.\d+$') {
  Fail "Версия должна быть в формате X.Y.Z (например, 1.2.3)"
}

# 2) git checks
$branch = (git rev-parse --abbrev-ref HEAD) 2>$null
if (-not $branch) { Fail "Git не найден в PATH" }

if ($branch -ne "main") {
  Write-Warning "Сейчас ветка: $branch (не main). Продолжаю..."
}

$dirty = git status --porcelain
if ($dirty) {
  Fail "Рабочее дерево не чистое. Закоммить/откати изменения и повтори."
}

# 3) защита от существующих тегов
$checkTag = {
  param([string]$Tag)
  git rev-parse $Tag 2>$null | Out-Null
  if ($LASTEXITCODE -eq 0) { Fail "Тег $Tag уже существует" }
}

if ($Service -in @("back","both")) {
  & $checkTag "back-v$Version"
}
if ($Service -in @("front","both")) {
  & $checkTag "front-v$Version"
}

# 4) правки версий
$didAnyChange = $false

if ($Service -in @("back","both")) {
  # Обновляем глобальный VERSION (для бэка)
  Set-Content -Path "VERSION" -Value $Version -NoNewline
  Write-Host "✔ VERSION -> $Version"
  $didAnyChange = $true
}

if ($Service -in @("front","both")) {
  $pkgPath = "frontend/package.json"
  if (Test-Path $pkgPath) {
    try {
      $json = Get-Content $pkgPath -Raw | ConvertFrom-Json
      $json.version = $Version
      $json | ConvertTo-Json -Depth 32 | Out-File $pkgPath -Encoding UTF8
      Write-Host "✔ $pkgPath -> version = $Version"
      $didAnyChange = $true
    } catch {
      Fail "Не удалось обновить $pkgPath: $($_.Exception.Message)"
    }
  } else {
    Fail "Не найден $pkgPath. Убедись, что папка называется 'frontend' и там есть package.json."
  }
}

if (-not $didAnyChange) {
  Fail "Нет изменений для коммита. Проверь входные параметры."
}

# 5) commit + tags
if (-not $NoCommit) {
  $scope = if ($Service -eq "both") { "back,front" } else { $Service }
  git add -A
  git commit -m "chore($scope): release v$Version" | Out-Null

  if ($Service -in @("back","both")) {
    git tag -a "back-v$Version" -m "Back release v$Version"
    Write-Host "✔ Тег создан: back-v$Version"
  }
  if ($Service -in @("front","both")) {
    git tag -a "front-v$Version" -m "Front release v$Version"
    Write-Host "✔ Тег создан: front-v$Version"
  }
} else {
  Write-Warning "--NoCommit: пропускаю git commit/tag"
}

# 6) push
if (-not $NoPush -and -not $NoCommit) {
  git push origin $branch
  if ($Service -in @("back","both")) { git push origin "back-v$Version" }
  if ($Service -in @("front","both")) { git push origin "front-v$Version" }
  Write-Host "🚀 Отправлено в origin: $branch и соответствующие теги"
} elseif ($NoPush) {
  Write-Warning "--NoPush: пуш пропущен"
}

Write-Host "Готово. Дождись CI: он соберёт и запушит образы в GHCR согласно тегам."
Write-Host "Напоминание: на сервере обновляй теги в .env (BACK_TAG/FRONT_TAG) и делай: docker compose pull && docker compose up -d <service>"
