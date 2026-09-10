$tracked = git ls-files
$forbidden = $tracked | Select-String -Pattern '(^|/)(oauth|browser|credentials).*\.json$|\.sqlite3?$|(^|/)\.env$|(^|/)dist/|(^|/)frontend/node_modules/'
if ($forbidden) { throw "Sensitive or generated runtime files are tracked." }
$scanFiles = $tracked | Where-Object { $_ -ne "scripts/check-secrets.ps1" }
$content = $scanFiles | ForEach-Object { Get-Content -LiteralPath $_ -Raw -ErrorAction SilentlyContinue }
$patterns = @(
  'BEGIN [A-Z ]+PRIVATE KEY',
  'access_token\s*[:=]\s*["''](?!dummy|example|secret|access|refresh|test|fake)[A-Za-z0-9._-]{20,}',
  'refresh_token\s*[:=]\s*["''](?!dummy|example|secret|access|refresh|test|fake)[A-Za-z0-9._-]{20,}',
  'client_secret\s*[:=]\s*["''](?!dummy|example|secret|access|refresh|test|fake)[A-Za-z0-9._-]{20,}'
)
foreach ($pattern in $patterns) {
  if ($content -match $pattern) { throw "Potential secret pattern found: $pattern" }
}
git diff --check
Write-Output "Secret and artifact scan passed."
