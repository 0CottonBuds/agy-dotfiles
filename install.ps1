<#
.SYNOPSIS
    Migrates Antigravity global customizations from this repo into %USERPROFILE%\.gemini\config on Windows.
.DESCRIPTION
    Creates directory Junctions for rules, skills, and hooks (no Admin required),
    links AGENTS.md and skills.json (SymbolicLink -> HardLink -> Copy fallback),
    generates a Windows-native hooks.json without UTF-8 BOM, syncs community skills
    into %USERPROFILE%\.agents\skills, and runs the validation + safety-guard test suite.
#>
[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$SkipCommunity,
    [switch]$UpdateCommunity,
    [switch]$NoVerify
)

$ErrorActionPreference = 'Stop'

$RepoDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ConfigDir = Join-Path $env:USERPROFILE '.gemini\config'
$AgentsSkillsDir = Join-Path $env:USERPROFILE '.agents\skills'
$Timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$BackupDir = Join-Path $ConfigDir (".backup-agy-dotfiles-" + $Timestamp)
$script:BackupUsed = $false
$script:CopyFallbacks = New-Object System.Collections.Generic.List[string]

function Ensure-BackupDir {
    if (-not $script:BackupUsed) {
        New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
        $script:BackupUsed = $true
    }
}

function Normalize-PathStr([string]$PathValue) {
    return ([System.IO.Path]::GetFullPath($PathValue)).TrimEnd('\', '/')
}

function Test-IsReparsePoint([string]$PathValue) {
    if (-not (Test-Path -LiteralPath $PathValue)) {
        return $false
    }
    $item = Get-Item -LiteralPath $PathValue -Force
    return (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0)
}

function Get-ReparseTargetNormalized([string]$PathValue) {
    $item = Get-Item -LiteralPath $PathValue -Force
    $rawTarget = $null
    if ($item.PSObject.Properties.Match('Target').Count -gt 0 -and $item.Target) {
        if ($item.Target -is [System.Array]) {
            $rawTarget = [string]$item.Target[0]
        } else {
            $rawTarget = [string]$item.Target
        }
    }
    if ([string]::IsNullOrWhiteSpace($rawTarget)) {
        return ''
    }
    try {
        return (Normalize-PathStr $rawTarget)
    } catch {
        return $rawTarget.TrimEnd('\', '/')
    }
}

function Find-Python {
    $candidates = @(
        @{ Exe = 'py'; PrefixArgs = @('-3'); HookCmd = 'py -3' },
        @{ Exe = 'python'; PrefixArgs = @(); HookCmd = 'python' },
        @{ Exe = 'python3'; PrefixArgs = @(); HookCmd = 'python3' }
    )

    foreach ($cand in $candidates) {
        $cmdInfo = Get-Command $cand.Exe -ErrorAction SilentlyContinue
        if (-not $cmdInfo) {
            continue
        }
        $checkArgs = @()
        $checkArgs += $cand.PrefixArgs
        $checkArgs += @('-c', 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)')
        try {
            $null = & $cand.Exe @checkArgs 2>$null
            if ($LASTEXITCODE -eq 0) {
                return $cand
            }
        } catch {
            continue
        }
    }

    throw "Python 3.9+ was not found (Windows Store stubs are ignored). Install Python 3.12+ (e.g. 'winget install Python.Python.3.12') and re-run .\install.ps1."
}

function Test-SameFileViaPython($PyInfo, [string]$PathA, [string]$PathB) {
    $args = @()
    $args += $PyInfo.PrefixArgs
    $args += @('-c', 'import os, sys; raise SystemExit(0 if os.path.samefile(sys.argv[1], sys.argv[2]) else 1)', $PathA, $PathB)
    try {
        $null = & $PyInfo.Exe @args 2>$null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Link-DirectoryItem([string]$Name) {
    $src = Join-Path $RepoDir $Name
    $dst = Join-Path $ConfigDir $Name
    if (-not (Test-Path -LiteralPath $src -PathType Container)) {
        throw "Missing directory in repo: $src"
    }
    $srcNorm = Normalize-PathStr $src

    if (Test-Path -LiteralPath $dst) {
        if (Test-IsReparsePoint $dst) {
            $curTarget = Get-ReparseTargetNormalized $dst
            if ($curTarget -ieq $srcNorm) {
                Write-Host "OK (already linked): $Name"
                return
            }
            if ($DryRun) {
                Write-Host "[dry-run] replace stale junction: $dst -> $src"
                return
            }
            [System.IO.Directory]::Delete($dst)
            New-Item -ItemType Junction -Path $dst -Target $src | Out-Null
            Write-Host "Relinked junction: $Name -> $src"
            return
        }

        if ($DryRun) {
            Write-Host "[dry-run] backup $dst -> $BackupDir\$Name && junction $dst -> $src"
            return
        }
        Ensure-BackupDir
        Move-Item -LiteralPath $dst -Destination (Join-Path $BackupDir $Name)
        New-Item -ItemType Junction -Path $dst -Target $src | Out-Null
        Write-Host "Migrated (backed up old $Name): $Name -> $src"
        return
    }

    if ($DryRun) {
        Write-Host "[dry-run] junction $dst -> $src"
        return
    }
    New-Item -ItemType Junction -Path $dst -Target $src | Out-Null
    Write-Host "Linked junction: $Name -> $src"
}

function Link-FileItem([string]$Name, $PyInfo) {
    $src = Join-Path $RepoDir $Name
    $dst = Join-Path $ConfigDir $Name
    if (-not (Test-Path -LiteralPath $src -PathType Leaf)) {
        throw "Missing file in repo: $src"
    }
    $srcNorm = Normalize-PathStr $src

    if (Test-Path -LiteralPath $dst) {
        if (Test-IsReparsePoint $dst) {
            $curTarget = Get-ReparseTargetNormalized $dst
            if ($curTarget -ieq $srcNorm) {
                Write-Host "OK (already linked): $Name"
                return
            }
            if ($DryRun) {
                Write-Host "[dry-run] replace stale file symlink: $dst -> $src"
                return
            }
            [System.IO.File]::Delete($dst)
        } else {
            $item = Get-Item -LiteralPath $dst -Force
            if ((-not $item.PSIsContainer) -and (Test-SameFileViaPython $PyInfo $src $dst)) {
                Write-Host "OK (already hard-linked): $Name"
                return
            }
            if ($DryRun) {
                Write-Host "[dry-run] backup $dst -> $BackupDir\$Name && link $dst -> $src"
                return
            }
            Ensure-BackupDir
            Move-Item -LiteralPath $dst -Destination (Join-Path $BackupDir $Name)
        }
    } elseif ($DryRun) {
        Write-Host "[dry-run] link file $dst -> $src"
        return
    }

    try {
        New-Item -ItemType SymbolicLink -Path $dst -Target $src -ErrorAction Stop | Out-Null
        Write-Host "Linked symlink: $Name -> $src"
        return
    } catch {
        # Unprivileged Windows accounts without Developer Mode cannot create file symlinks; try NTFS hard link
    }

    try {
        New-Item -ItemType HardLink -Path $dst -Target $src -ErrorAction Stop | Out-Null
        Write-Host "Linked hardlink: $Name -> $src"
        return
    } catch {
        Copy-Item -LiteralPath $src -Destination $dst -Force
        $script:CopyFallbacks.Add($Name)
        Write-Warning "Copied '$Name' (cross-drive fallback; re-run .\install.ps1 after 'git pull')."
    }
}

function Render-HooksJson($PyInfo) {
    $tplPath = Join-Path $RepoDir 'hooks.template.json'
    $dstPath = Join-Path $ConfigDir 'hooks.json'
    $tpl = [System.IO.File]::ReadAllText($tplPath, [System.Text.Encoding]::UTF8)
    $rendered = $tpl.Replace('{{PYTHON_CMD}}', $PyInfo.HookCmd).Replace('{{HOOK_SCRIPT}}', 'hooks\\safety_guard.py')

    if ((Test-Path -LiteralPath $dstPath -PathType Leaf) -and (-not (Test-IsReparsePoint $dstPath))) {
        $existing = [System.IO.File]::ReadAllText($dstPath, [System.Text.Encoding]::UTF8)
        if ($existing -ceq $rendered) {
            Write-Host "OK (up to date): hooks.json"
            return
        }
    }

    if ($DryRun) {
        Write-Host "[dry-run] generate $dstPath (command: $($PyInfo.HookCmd) hooks\safety_guard.py)"
        return
    }

    if (Test-Path -LiteralPath $dstPath) {
        if (Test-IsReparsePoint $dstPath) {
            [System.IO.File]::Delete($dstPath)
        } else {
            Ensure-BackupDir
            Move-Item -LiteralPath $dstPath -Destination (Join-Path $BackupDir 'hooks.json')
        }
    }

    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($dstPath, $rendered, $utf8NoBom)
    Write-Host "Generated: hooks.json ($($PyInfo.HookCmd) hooks\safety_guard.py)"
}

function Sync-CommunitySkills {
    if ($SkipCommunity) {
        Write-Host "Skipped community skills (-SkipCommunity)."
        return
    }
    $listFile = Join-Path $RepoDir 'community-skills.txt'
    if (-not (Test-Path -LiteralPath $listFile -PathType Leaf)) {
        return
    }

    $hasNpx = [bool](Get-Command npx -ErrorAction SilentlyContinue)
    foreach ($rawLine in [System.IO.File]::ReadAllLines($listFile)) {
        $line = ($rawLine -replace '#.*$', '').Trim()
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }
        $parts = $line -split '\s+'
        if ($parts.Count -lt 2) {
            continue
        }
        $repo = $parts[0]
        $skill = $parts[1]
        $skillMd = Join-Path (Join-Path $AgentsSkillsDir $skill) 'SKILL.md'

        if ((Test-Path -LiteralPath $skillMd -PathType Leaf) -and (-not $UpdateCommunity)) {
            Write-Host "OK (installed): $skill"
            continue
        }

        if ($DryRun) {
            Write-Host "[dry-run] npx -y skills add $repo --skill $skill -g -y"
            continue
        }

        if (-not $hasNpx) {
            Write-Warning "npx not found; install '$skill' later with: npx -y skills add $repo --skill $skill -g -y"
            continue
        }

        & npx -y skills add $repo --skill $skill -g -y
        if ($LASTEXITCODE -ne 0) {
            throw "Failed installing community skill '$skill' from '$repo'."
        }

        $repoSkillPath = Join-Path (Join-Path $RepoDir 'skills') $skill
        if (Test-IsReparsePoint $repoSkillPath) {
            [System.IO.Directory]::Delete($repoSkillPath)
        }
    }
}

function Invoke-PostVerification($PyInfo) {
    if ($DryRun -or $NoVerify) {
        return
    }

    Write-Host "=== Running post-install verification ==="
    $validator = Join-Path $ConfigDir 'skills\repo-customization-bootstrap\scripts\validate_customizations.py'
    $guardTest = Join-Path $RepoDir 'scripts\test_safety_guard.py'
    $hookScript = Join-Path $ConfigDir 'hooks\safety_guard.py'

    $v1 = @() + $PyInfo.PrefixArgs + @($validator, '--target', $ConfigDir)
    & $PyInfo.Exe @v1
    if ($LASTEXITCODE -ne 0) { throw "Customization validation failed for $ConfigDir" }

    $agentsDir = Join-Path $env:USERPROFILE '.agents'
    if (Test-Path -LiteralPath $agentsDir -PathType Container) {
        $v2 = @() + $PyInfo.PrefixArgs + @($validator, '--target', $agentsDir)
        & $PyInfo.Exe @v2
        if ($LASTEXITCODE -ne 0) { throw "Customization validation failed for $agentsDir" }
    }

    $t1 = @() + $PyInfo.PrefixArgs + @($guardTest, '--hook', $hookScript)
    & $PyInfo.Exe @t1
    if ($LASTEXITCODE -ne 0) { throw "Safety guard test suite failed." }
}

$pyInfo = Find-Python
Write-Host "Repo:   $RepoDir"
Write-Host "Target: $ConfigDir"
Write-Host "Python: $($pyInfo.HookCmd)"

if (-not $DryRun) {
    if (-not (Test-Path -LiteralPath $ConfigDir -PathType Container)) {
        New-Item -ItemType Directory -Path $ConfigDir -Force | Out-Null
    }
    if (-not (Test-Path -LiteralPath $AgentsSkillsDir -PathType Container)) {
        New-Item -ItemType Directory -Path $AgentsSkillsDir -Force | Out-Null
    }
} else {
    if (-not (Test-Path -LiteralPath $ConfigDir -PathType Container)) {
        Write-Host "[dry-run] mkdir $ConfigDir"
    }
    if (-not (Test-Path -LiteralPath $AgentsSkillsDir -PathType Container)) {
        Write-Host "[dry-run] mkdir $AgentsSkillsDir"
    }
}

foreach ($dirName in @('rules', 'skills', 'hooks')) {
    Link-DirectoryItem $dirName
}
foreach ($fileName in @('AGENTS.md', 'skills.json')) {
    Link-FileItem $fileName $pyInfo
}

Render-HooksJson $pyInfo
Sync-CommunitySkills
Invoke-PostVerification $pyInfo

Write-Host ""
if ($DryRun) {
    Write-Host "Dry run complete. No files were modified."
} else {
    Write-Host "Windows Antigravity migration complete."
    if ($script:BackupUsed) {
        Write-Host "Backups saved to: $BackupDir"
    }
    if ($script:CopyFallbacks.Count -gt 0) {
        Write-Warning ("Cross-drive copy fallback used for: " + ($script:CopyFallbacks -join ', ') + ". Re-run .\install.ps1 after git pull.")
    }
    Write-Host "Start a new Antigravity conversation (or run /skills reload in CLI) to apply changes."
}
