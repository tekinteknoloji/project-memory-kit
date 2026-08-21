$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$temporaryProfile = Join-Path ([System.IO.Path]::GetTempPath()) ("project-memory-ci-" + [guid]::NewGuid().ToString('N'))
$originalProfile = $env:USERPROFILE
$env:USERPROFILE = $temporaryProfile
$env:PROJECT_MEMORY_NO_PAUSE = '1'

try {
    New-Item -ItemType Directory -Path $temporaryProfile | Out-Null
    Push-Location $repositoryRoot
    try {
        & cmd.exe /d /c 'PROJECT-MEMORY-KUR.cmd'
        if ($LASTEXITCODE -ne 0) { throw "Install failed: $LASTEXITCODE" }

        $skillFile = Join-Path $temporaryProfile '.codex\skills\project-memory\SKILL.md'
        $agentsFile = Join-Path $temporaryProfile '.codex\AGENTS.md'
        if (-not (Test-Path -LiteralPath $skillFile)) { throw 'Installed SKILL.md is missing.' }
        if (-not ((Get-Content -LiteralPath $agentsFile -Raw).Contains('<!-- project-memory:start -->'))) {
            throw 'Global memory rules were not installed.'
        }

        & cmd.exe /d /c 'PROJECT-MEMORY-GUNCELLE.cmd'
        if ($LASTEXITCODE -ne 0) { throw "Update failed: $LASTEXITCODE" }
        $backups = @(Get-ChildItem -LiteralPath (Join-Path $temporaryProfile '.codex\skills') -Directory -Filter 'project-memory.backup-*')
        if ($backups.Count -ne 1) { throw "Expected one update backup; found $($backups.Count)." }

        & cmd.exe /d /c 'PROJECT-MEMORY-KALDIR.cmd'
        if ($LASTEXITCODE -ne 0) { throw "Uninstall failed: $LASTEXITCODE" }
        if (Test-Path -LiteralPath (Split-Path -Parent $skillFile)) { throw 'Skill folder remains after uninstall.' }
        if ((Get-Content -LiteralPath $agentsFile -Raw).Contains('<!-- project-memory:start -->')) {
            throw 'Global memory rules remain after uninstall.'
        }
    } finally {
        Pop-Location
    }
} finally {
    $env:USERPROFILE = $originalProfile
    Remove-Item Env:PROJECT_MEMORY_NO_PAUSE -ErrorAction SilentlyContinue
}

Write-Host 'One-click install/update/uninstall test passed.'
