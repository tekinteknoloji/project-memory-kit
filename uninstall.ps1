[CmdletBinding(SupportsShouldProcess)]
param(
    [switch]$RemoveGlobalRules
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [Console]::OutputEncoding
$codexRoot = Join-Path $env:USERPROFILE '.codex'
$targetSkill = Join-Path $codexRoot 'skills\project-memory'

if (Test-Path -LiteralPath $targetSkill) {
    if ($PSCmdlet.ShouldProcess($targetSkill, 'Project Memory skill klasorunu kaldir')) {
        Remove-Item -LiteralPath $targetSkill -Recurse -Force
        Write-Host "Skill kaldirildi: $targetSkill"
    }
} else {
    Write-Host 'Project Memory skill kurulu degil.'
}

if ($RemoveGlobalRules) {
    $agentsPath = Join-Path $codexRoot 'AGENTS.md'
    if (Test-Path -LiteralPath $agentsPath) {
        $content = Get-Content -LiteralPath $agentsPath -Raw
        $pattern = '(?s)\r?\n?<!-- project-memory:start -->.*?<!-- project-memory:end -->\r?\n?'
        $updated = [regex]::Replace($content, $pattern, "`r`n").TrimEnd() + "`r`n"
        if ($updated -ne $content) {
            Copy-Item -LiteralPath $agentsPath -Destination "$agentsPath.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
            Set-Content -LiteralPath $agentsPath -Value $updated -Encoding utf8
            Write-Host "Global kurallar kaldirildi: $agentsPath"
        }
    }
}
