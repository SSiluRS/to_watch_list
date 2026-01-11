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
  Fail "Version must be in X.Y.Z format (e.g. 1.2.3)"
}

# 2) git checks
$branch = (git rev-parse --abbrev-ref HEAD) 2>$null
if (-not $branch) { Fail "Git not found in PATH" }

if ($branch -ne "main") {
  Write-Warning "Current branch: $branch (not main). Continuing..."
}

$dirty = git status --porcelain
if ($dirty) {
  Fail "Working tree is dirty. Commit or stash changes and retry."
}

# 3) protect against existing tags
$checkTag = {
  param([string]$Tag)
  git rev-parse $Tag 2>$null | Out-Null
  if ($LASTEXITCODE -eq 0) { Fail "Tag $Tag already exists" }
}

if ($Service -in @("back","both")) {
  & $checkTag "back-v$Version"
}
if ($Service -in @("front","both")) {
  & $checkTag "front-v$Version"
}

# 4) version updates
$didAnyChange = $false

if ($Service -in @("back","both")) {
  # Update global VERSION
  Set-Content -Path "VERSION" -Value $Version -NoNewline
  Write-Host "[OK] VERSION -> $Version"
  $didAnyChange = $true
}

if ($Service -in @("front","both")) {
  $pkgPath = "frontend/package.json"
  if (Test-Path $pkgPath) {
    try {
      $json = Get-Content $pkgPath -Raw | ConvertFrom-Json
      $json.version = $Version
      # Use UTF8 without BOM and 2-space indentation
      $jsonContent = $json | ConvertTo-Json -Depth 32
      $jsonContent = $jsonContent -replace '    ', '  '
      [System.IO.File]::WriteAllText((Resolve-Path $pkgPath), $jsonContent, (New-Object System.Text.UTF8Encoding($false)))
      Write-Host "[OK] $pkgPath -> version = $Version"
      $didAnyChange = $true
    } catch {
      $errMsg = $_.Exception.Message
      Fail "Failed to update $pkgPath : $errMsg"
    }
  } else {
    Fail "$pkgPath not found."
  }
}

if (-not $didAnyChange) {
  Fail "No changes to commit."
}

# 5) commit + tags
if (-not $NoCommit) {
  $scope = if ($Service -eq "both") { "back,front" } else { $Service }
  git add -A
  git commit -m "chore($scope): release v$Version" | Out-Null

  if ($Service -in @("back","both")) {
    git tag -a "back-v$Version" -m "Back release v$Version"
    Write-Host "[OK] Tag created: back-v$Version"
  }
  if ($Service -in @("front","both")) {
    git tag -a "front-v$Version" -m "Front release v$Version"
    Write-Host "[OK] Tag created: front-v$Version"
  }
} else {
  Write-Warning "--NoCommit: skipping git commit/tag"
}

# 6) push
if (-not $NoPush -and -not $NoCommit) {
  git push origin $branch
  if ($Service -in @("back","both")) { git push origin "back-v$Version" }
  if ($Service -in @("front","both")) { git push origin "front-v$Version" }
  Write-Host "[OK] Pushed to origin: $branch and tags"
} elseif ($NoPush) {
  Write-Warning "--NoPush: skipping push"
}

Write-Host "Done. CI will build and push images."
Write-Host "Reminder: update tags in .env (BACK_TAG/FRONT_TAG) on server and run: docker compose pull && docker compose up -d"