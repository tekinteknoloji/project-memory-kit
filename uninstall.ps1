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
        $content = [IO.File]::ReadAllText($agentsPath, [Text.Encoding]::UTF8)
        $pattern = '(?s)<!-- project-memory:start -->.*?<!-- project-memory:end -->'
        $updated = [regex]::Replace($content, $pattern, '')
        if ($updated -ne $content -and $PSCmdlet.ShouldProcess($agentsPath, 'Project Memory global kurallarini kaldir')) {
            Copy-Item -LiteralPath $agentsPath -Destination "$agentsPath.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
            [IO.File]::WriteAllText($agentsPath, $updated, [Text.UTF8Encoding]::new($false))
            Write-Host "Global kurallar kaldirildi: $agentsPath"
        }
    }
}
