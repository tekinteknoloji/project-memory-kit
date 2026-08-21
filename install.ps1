[CmdletBinding()]
param(
    [switch]$InstallGlobalRules,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [Console]::OutputEncoding
$kitRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceSkill = Join-Path $kitRoot 'plugins\project-memory\skills\project-memory'
$codexRoot = Join-Path $env:USERPROFILE '.codex'
$skillsRoot = Join-Path $codexRoot 'skills'
$targetSkill = Join-Path $skillsRoot 'project-memory'

if (-not (Test-Path -LiteralPath (Join-Path $sourceSkill 'SKILL.md'))) {
    throw "Paket gecersiz: project-memory/SKILL.md bulunamadi."
}

New-Item -ItemType Directory -Path $skillsRoot -Force | Out-Null

if (Test-Path -LiteralPath $targetSkill) {
    if (-not $Force) {
        throw "Skill zaten kurulu: $targetSkill. Guncellemek icin -Force kullanin."
    }
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $backup = "$targetSkill.backup-$stamp"
    Move-Item -LiteralPath $targetSkill -Destination $backup
    Write-Host "Onceki skill yedeklendi: $backup"
}

$temporaryTarget = "$targetSkill.installing"
if (Test-Path -LiteralPath $temporaryTarget) {
    Remove-Item -LiteralPath $temporaryTarget -Recurse -Force
}

Copy-Item -LiteralPath $sourceSkill -Destination $temporaryTarget -Recurse
Move-Item -LiteralPath $temporaryTarget -Destination $targetSkill
Write-Host "Project Memory kuruldu: $targetSkill"

if ($InstallGlobalRules) {
    $agentsPath = Join-Path $codexRoot 'AGENTS.md'
    $snippetPath = Join-Path $kitRoot 'global\AGENTS.snippet.md'
    $startMarker = '<!-- project-memory:start -->'
    $existing = if (Test-Path -LiteralPath $agentsPath) {
        Get-Content -LiteralPath $agentsPath -Raw
    } else {
        ''
    }

    if ($existing.Contains($startMarker)) {
        Write-Host "Global kurallar zaten mevcut: $agentsPath"
    } else {
        New-Item -ItemType Directory -Path $codexRoot -Force | Out-Null
        if ($existing.Length -gt 0) {
            Copy-Item -LiteralPath $agentsPath -Destination "$agentsPath.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
            Add-Content -LiteralPath $agentsPath -Value "`r`n"
        }
        Add-Content -LiteralPath $agentsPath -Value (Get-Content -LiteralPath $snippetPath -Raw)
        Write-Host "Global otomatik baslatma kurallari eklendi: $agentsPath"
    }
}

Write-Host 'Kurulum tamamlandi. Codex icinde yeni bir gorev acarak test edin.'
