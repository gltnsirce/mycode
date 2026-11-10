
# ============================================================
# Chrome DevTools Configuration Manager
# Windows 11 / PowerShell 5.1+
#
# Functions:
# 1. Detect Windows and Chrome versions
# 2. Detect default HTTP/HTTPS browser
# 3. Discover ALL Chrome profiles
# 4. Check 5 DevTools settings
# 5. Automatically enable 4 persistent settings
# 6. Backup Preferences before modification
# 7. Recheck settings after modification
# 8. Report settings requiring manual verification
#
# Author: GltnsRice
# Email: yiming.yin@outlook.com
#
# How to run this script without administrator permission:
# - Direct run the command: powershell -ExecutionPolicy Bypass -File ".\check_chrome_devtool.ps1"
# or
# - Run the command "Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass" to setup the exceution policy, then direct run the script/
#
# IMPORTANT:
# Close Chrome before running to allow modifications.
# ============================================================

$ErrorActionPreference = "Stop"

# ------------------------------------------------------------
# Configuration definitions
# ------------------------------------------------------------

$DevToolsSettings = @(
    [PSCustomObject]@{
        Category = "Network"
        Name = "Preserve log"
        Key = "network_log.preserve-log"
        Persistent = $false
    },
    [PSCustomObject]@{
        Category = "Network"
        Name = "Allow HAR with sensitive data"
        Key = "network.show-options-to-generate-har-with-sensitive-data"
        Persistent = $true
    },
    [PSCustomObject]@{
        Category = "Console"
        Name = "Log XMLHttpRequests"
        Key = "monitoringXHREnabled"
        Persistent = $true
    },
    [PSCustomObject]@{
        Category = "Console"
        Name = "Show timestamps"
        Key = "consoleTimestampsEnabled"
        Persistent = $true
    },
    [PSCustomObject]@{
        Category = "Console"
        Name = "Preserve log upon navigation"
        Key = "preserveConsoleLog"
        Persistent = $true
    }
)

# ------------------------------------------------------------
# Helper: Read a DevTools preference
# ------------------------------------------------------------

function Get-SettingStatus {
    param(
        $Preferences,
        [string]$Key
    )

    if ($null -eq $Preferences) {
        return "DISABLED"
    }

    $property = $Preferences.PSObject.Properties[$Key]

    # These four persistent settings have false defaults.
    if ($null -eq $property) {
        return "DISABLED"
    }

    $value = $property.Value

    if ($value -is [bool]) {
        if ($value) { return "ENABLED" }
        return "DISABLED"
    }

    if ($value -is [string]) {
        if ($value -ieq "true") { return "ENABLED" }
        if ($value -ieq "false") { return "DISABLED" }
    }

    return "MANUAL CHECK"
}

# ------------------------------------------------------------
# Helper: Enable a persistent preference
# ------------------------------------------------------------

function Enable-Setting {
    param(
        $Preferences,
        [string]$Key
    )

    $property = $Preferences.PSObject.Properties[$Key]

    if ($null -eq $property) {
        $Preferences | Add-Member `
            -MemberType NoteProperty `
            -Name $Key `
            -Value "true"

        return $true
    }

    if ($property.Value -is [bool]) {
        $property.Value = $true
        return $true
    }

    if ($property.Value -is [string]) {
        if ($property.Value -ieq "true") {
            return $true
        }

        if ($property.Value -ieq "false") {
            $property.Value = "true"
            return $true
        }
    }

    return $false
}

# ------------------------------------------------------------
# Helper: Get nested DevTools preferences
# ------------------------------------------------------------

function Get-DevToolsPreferences {
    param($Json)

    $devtoolsProperty = $Json.PSObject.Properties["devtools"]

    if ($null -eq $devtoolsProperty) {
        return $null
    }

    $preferencesProperty =
        $devtoolsProperty.Value.PSObject.Properties["preferences"]

    if ($null -eq $preferencesProperty) {
        return $null
    }

    return $preferencesProperty.Value
}

# ------------------------------------------------------------
# 1. SYSTEM INFORMATION
# ------------------------------------------------------------

$os = Get-CimInstance Win32_OperatingSystem
$cv = Get-ItemProperty `
    "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion"

$chromePaths = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)

$chromePath = $chromePaths |
    Where-Object { $_ -and (Test-Path $_) } |
    Select-Object -First 1

$chromeVersion = "NOT FOUND"

if ($chromePath) {
    $chromeVersion = (Get-Item $chromePath).VersionInfo.ProductVersion
}

Write-Host "`n================================================"
Write-Host " SYSTEM INFORMATION" -ForegroundColor Cyan
Write-Host "================================================"

Write-Host "Windows       : $($os.Caption)"
Write-Host "Windows Build : $($cv.CurrentBuild).$($cv.UBR)"
Write-Host "Chrome        : $chromeVersion"
Write-Host "PowerShell    : $($PSVersionTable.PSVersion)"

# ------------------------------------------------------------
# 2. DEFAULT BROWSER
# ------------------------------------------------------------

Write-Host "`n================================================"
Write-Host " DEFAULT BROWSER" -ForegroundColor Cyan
Write-Host "================================================"

foreach ($scheme in @("http", "https")) {

    $key = "HKCU:\Software\Microsoft\Windows\Shell\Associations\UrlAssociations\$scheme\UserChoice"

    $progId = "UNKNOWN"

    if (Test-Path $key) {
        $result = Get-ItemProperty -LiteralPath $key
        if ($result.ProgId) {
            $progId = $result.ProgId
        }
    }

    $display = switch -Wildcard ($progId) {
        "ChromeHTML*" { "Google Chrome ($progId)" }
        "MSEdgeHTM*"  { "Microsoft Edge ($progId)" }
        default       { $progId }
    }

    Write-Host "$scheme : $display"
}

# ------------------------------------------------------------
# 3. CHROME PROFILE DISCOVERY
# ------------------------------------------------------------

$userData = Join-Path $env:LOCALAPPDATA `
    "Google\Chrome\User Data"

if (-not (Test-Path $userData)) {
    Write-Host "`nChrome User Data directory not found." `
        -ForegroundColor Red
    exit 1
}

$profiles = @(
    Get-ChildItem -LiteralPath $userData -Directory |
    Where-Object {
        Test-Path (Join-Path $_.FullName "Preferences")
    }
)

if ($profiles.Count -eq 0) {
    Write-Host "No Chrome profiles found." -ForegroundColor Red
    exit 1
}

Write-Host "`n================================================"
Write-Host " CHROME PROFILES: $($profiles.Count)" -ForegroundColor Cyan
Write-Host "================================================"

foreach ($profile in $profiles) {
    Write-Host " - $($profile.Name)"
}

# ------------------------------------------------------------
# 4. CHECK CHROME RUNNING STATUS
# ------------------------------------------------------------

$chromeRunning = $null -ne (Get-Process chrome -ErrorAction SilentlyContinue)

if ($chromeRunning) {
    Write-Host "`nWARNING: Chrome is currently running." `
        -ForegroundColor Yellow

    Write-Host "Automatic modification will be skipped."
    Write-Host "Close ALL Chrome windows and rerun this script."
}

# ------------------------------------------------------------
# 5. INITIAL CONFIGURATION CHECK
# ------------------------------------------------------------

$initialResults = @()
$finalResults = @()

foreach ($profile in $profiles) {

    $prefFile = Join-Path $profile.FullName "Preferences"

    try {
        $json = Get-Content -LiteralPath $prefFile -Raw |
            ConvertFrom-Json -ErrorAction Stop

        $preferences = Get-DevToolsPreferences -Json $json

        foreach ($setting in $DevToolsSettings) {

            if (-not $setting.Persistent) {
                $status = "MANUAL CHECK"
            }
            else {
                $status = Get-SettingStatus `
                    -Preferences $preferences `
                    -Key $setting.Key
            }

            $initialResults += [PSCustomObject]@{
                Profile = $profile.Name
                Category = $setting.Category
                Setting = $setting.Name
                Status = $status
            }
        }
    }
    catch {
        foreach ($setting in $DevToolsSettings) {
            $initialResults += [PSCustomObject]@{
                Profile = $profile.Name
                Category = $setting.Category
                Setting = $setting.Name
                Status = "MANUAL CHECK"
            }
        }
    }
}

Write-Host "`n================================================"
Write-Host " INITIAL CONFIGURATION" -ForegroundColor Cyan
Write-Host "================================================"

$initialResults |
    Format-Table Profile, Category, Setting, Status -AutoSize -Wrap

# ------------------------------------------------------------
# 6. AUTOMATIC MODIFICATION
# ------------------------------------------------------------

if (-not $chromeRunning) {

    Write-Host "`n================================================"
    Write-Host " AUTOMATIC CONFIGURATION" -ForegroundColor Cyan
    Write-Host "================================================"

    foreach ($profile in $profiles) {

        $prefFile = Join-Path $profile.FullName "Preferences"

        try {
            $json = Get-Content -LiteralPath $prefFile -Raw |
                ConvertFrom-Json -ErrorAction Stop

            $preferences = Get-DevToolsPreferences -Json $json

            # Create DevTools preference structure if missing.
            if ($null -eq $preferences) {

                if ($null -eq $json.PSObject.Properties["devtools"]) {
                    $json | Add-Member `
                        -MemberType NoteProperty `
                        -Name "devtools" `
                        -Value ([PSCustomObject]@{})
                }

                $devtools = $json.devtools

                if ($null -eq $devtools.PSObject.Properties["preferences"]) {
                    $devtools | Add-Member `
                        -MemberType NoteProperty `
                        -Name "preferences" `
                        -Value ([PSCustomObject]@{})
                }

                $preferences = $devtools.preferences
            }

            $changed = $false

            foreach ($setting in $DevToolsSettings) {

                # Session-scoped setting must be checked manually.
                if (-not $setting.Persistent) {
                    continue
                }

                $status = Get-SettingStatus `
                    -Preferences $preferences `
                    -Key $setting.Key

                if ($status -eq "DISABLED") {

                    $success = Enable-Setting `
                        -Preferences $preferences `
                        -Key $setting.Key

                    if ($success) {
                        $changed = $true
                        Write-Host "[$($profile.Name)] Enabled: $($setting.Name)"
                    }
                    else {
                        Write-Host "[$($profile.Name)] MANUAL: $($setting.Name)" `
                            -ForegroundColor Yellow
                    }
                }
                elseif ($status -eq "MANUAL CHECK") {
                    Write-Host "[$($profile.Name)] MANUAL: $($setting.Name)" `
                        -ForegroundColor Yellow
                }
            }

            if ($changed) {

                # Backup original Preferences.
                $backup = "$prefFile.bak_$(Get-Date -Format 'yyyyMMdd_HHmmss')"

                Copy-Item -LiteralPath $prefFile `
                    -Destination $backup -ErrorAction Stop

                # Write to a temporary file first.
                $tempFile = "$prefFile.tmp"

                $output = ConvertTo-Json -InputObject $json `
                    -Depth 100 -Compress

                [System.IO.File]::WriteAllText(
                    $tempFile,
                    $output,
                    (New-Object System.Text.UTF8Encoding($false))
                )

                # Atomic replacement on the same volume.
                [System.IO.File]::Replace(
                    $tempFile,
                    $prefFile,
                    $null
                )

                Write-Host "[$($profile.Name)] Backup created." `
                    -ForegroundColor Green
            }
            else {
                Write-Host "[$($profile.Name)] No changes required."
            }
        }
        catch {
            Write-Host "[$($profile.Name)] ERROR: $($_.Exception.Message)" `
                -ForegroundColor Red
        }
    }
}
else {
    Write-Host "`nModification skipped because Chrome is running." `
        -ForegroundColor Yellow
}

# ------------------------------------------------------------
# 7. FINAL VERIFICATION
# ------------------------------------------------------------

foreach ($profile in $profiles) {

    $prefFile = Join-Path $profile.FullName "Preferences"

    try {
        $json = Get-Content -LiteralPath $prefFile -Raw |
            ConvertFrom-Json -ErrorAction Stop

        $preferences = Get-DevToolsPreferences -Json $json

        foreach ($setting in $DevToolsSettings) {

            if (-not $setting.Persistent) {
                $status = "MANUAL CHECK"
            }
            else {
                $status = Get-SettingStatus `
                    -Preferences $preferences `
                    -Key $setting.Key
            }

            $finalResults += [PSCustomObject]@{
                Profile = $profile.Name
                Category = $setting.Category
                Setting = $setting.Name
                Status = $status
            }
        }
    }
    catch {
        foreach ($setting in $DevToolsSettings) {
            $finalResults += [PSCustomObject]@{
                Profile = $profile.Name
                Category = $setting.Category
                Setting = $setting.Name
                Status = "MANUAL CHECK"
            }
        }
    }
}

Write-Host "`n================================================"
Write-Host " FINAL VERIFICATION" -ForegroundColor Cyan
Write-Host "================================================"

$finalResults |
    Format-Table Profile, Category, Setting, Status -AutoSize -Wrap

# ------------------------------------------------------------
# 8. SUMMARY
# ------------------------------------------------------------

$enabledCount = @(
    $finalResults | Where-Object { $_.Status -eq "ENABLED" }
).Count

$disabledCount = @(
    $finalResults | Where-Object { $_.Status -eq "DISABLED" }
).Count

$manualCount = @(
    $finalResults | Where-Object { $_.Status -eq "MANUAL CHECK" }
).Count

Write-Host "`n================================================"
Write-Host " SUMMARY" -ForegroundColor Cyan
Write-Host "================================================"

Write-Host "Profiles checked : $($profiles.Count)"
Write-Host "Enabled          : $enabledCount"
Write-Host "Disabled         : $disabledCount"
Write-Host "Manual check     : $manualCount"

if ($manualCount -gt 0) {
    Write-Host "`nManual verification required:" -ForegroundColor Yellow

    $finalResults |
        Where-Object { $_.Status -eq "MANUAL CHECK" } |
        ForEach-Object {
            Write-Host "[$($_.Profile)] $($_.Setting)"
        }
}

if ($chromeRunning) {
    Write-Host "`nACTION: Close Chrome and rerun this script." `
        -ForegroundColor Yellow
}
elseif ($disabledCount -eq 0 -and $manualCount -eq 0) {
    Write-Host "`nALL SETTINGS ENABLED." -ForegroundColor Green
}
else {
    Write-Host "`nCHECK COMPLETED. Review manual items above." `
        -ForegroundColor Yellow
}

Write-Host "`n================================================"
Write-Host " SCRIPT COMPLETED" -ForegroundColor Cyan
Write-Host "================================================"
