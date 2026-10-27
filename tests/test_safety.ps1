$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$temporaryProfile = Join-Path ([IO.Path]::GetTempPath()) ("project-memory-safety-" + [guid]::NewGuid().ToString('N'))
$originalProfile = $env:USERPROFILE
$env:USERPROFILE = $temporaryProfile
try {
    & (Join-Path $repositoryRoot 'install.ps1') -InstallGlobalRules
    $skillPath = Join-Path $temporaryProfile '.codex\skills\project-memory'
    $agentsPath = Join-Path $temporaryProfile '.codex\AGENTS.md'
    $sentinel = Join-Path $skillPath 'preserve.txt'
    [IO.File]::WriteAllText($sentinel, 'preserve installed custom file')
    [IO.File]::AppendAllText($agentsPath, "`r`n# User rule: Türkçe, şifre yok.`r`n")
    $agentsBefore = [Convert]::ToBase64String([IO.File]::ReadAllBytes($agentsPath))
    & (Join-Path $repositoryRoot 'uninstall.ps1') -RemoveGlobalRules -WhatIf
    if (-not (Test-Path -LiteralPath $sentinel)) { throw 'WhatIf deleted installed files.' }
    if ([Convert]::ToBase64String([IO.File]::ReadAllBytes($agentsPath)) -ne $agentsBefore) { throw 'WhatIf modified global rules.' }
    if (@(Get-ChildItem -LiteralPath (Split-Path $agentsPath) -Filter 'AGENTS.md.backup-*').Count -ne 0) { throw 'WhatIf created backups.' }

    # Simulate a failed final rename after backing up the installed skill.
    function Move-Item {
        param([string]$LiteralPath, [string]$Destination)
        if ($LiteralPath -like '*.installing-*') { throw 'Injected final rename failure' }
        Microsoft.PowerShell.Management\Move-Item -LiteralPath $LiteralPath -Destination $Destination
    }
    $failed = $false
    try { & (Join-Path $repositoryRoot 'install.ps1') -Force -InstallGlobalRules }
    catch { $failed = $true }
    finally { Remove-Item Function:\Move-Item }
    if (-not $failed) { throw 'Expected injected update failure.' }
    if (-not (Test-Path -LiteralPath $sentinel)) { throw 'Update failed to restore original skill.' }
    if ([Convert]::ToBase64String([IO.File]::ReadAllBytes($agentsPath)) -ne $agentsBefore) { throw 'Failed update modified global rules.' }
    if (@(Get-ChildItem -LiteralPath (Split-Path $skillPath) -Filter '*.installing-*').Count -ne 0) { throw 'Staging files remain.' }
    & (Join-Path $repositoryRoot 'uninstall.ps1') -RemoveGlobalRules
    if (-not ([IO.File]::ReadAllText($agentsPath).Contains('# User rule: Türkçe, şifre yok.'))) { throw 'Uninstall lost unrelated user rules.' }
} finally {
    $env:USERPROFILE = $originalProfile
    $resolved = [IO.Path]::GetFullPath($temporaryProfile)
    $tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
    if ($resolved.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase) -and (Split-Path $resolved -Leaf) -like 'project-memory-safety-*') {
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
Write-Host 'Safety tests passed: WhatIf, rollback, preservation.'
