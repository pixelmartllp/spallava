<#
.SYNOPSIS
    Register the daily creative job with Windows Task Scheduler.

.DESCRIPTION
    By default this registers a GENERATE-ONLY task: every morning it renders
    the day's creatives and stops, so you can review them before anything goes
    live. Add -Publish to make the task post to Facebook and Instagram
    automatically as well.

.EXAMPLE
    # Generate 5 creatives every day at 08:00, review them yourself
    .\register_daily_task.ps1 -Time 08:00

.EXAMPLE
    # Fully automatic: generate at 09:30 and post to both platforms
    .\register_daily_task.ps1 -Time 09:30 -Publish

.EXAMPLE
    .\register_daily_task.ps1 -Remove
#>

[CmdletBinding()]
param(
    [string]$Time = "08:00",
    [int]$Count = 5,
    [switch]$Publish,
    [string]$Platforms = "facebook,instagram",
    [string]$TaskName = "ShashiPallava-DailyCreatives",
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $root ".venv\Scripts\pythonw.exe"
$script = Join-Path $root "daily_run.py"

if ($Remove) {
    $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($null -eq $existing) {
        Write-Output "No scheduled task named '$TaskName' found."
    } else {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Output "Removed scheduled task '$TaskName'."
    }
    return
}

if (-not (Test-Path $python)) {
    throw "Python venv not found at $python. Create it with: py -m venv .venv"
}
if (-not (Test-Path $script)) {
    throw "daily_run.py not found at $script"
}

if ($Publish) {
    $arguments = "`"$script`" auto --count $Count --platforms $Platforms --confirm"
    $mode = "GENERATE + PUBLISH (posts go live automatically)"
} else {
    $arguments = "`"$script`" generate --count $Count"
    $mode = "GENERATE ONLY (you review and publish manually)"
}

$action    = New-ScheduledTaskAction -Execute $python -Argument $arguments -WorkingDirectory $root
$trigger   = New-ScheduledTaskTrigger -Daily -At $Time
$settings  = New-ScheduledTaskSettingsSet -StartWhenAvailable `
                -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries `
                -ExecutionTimeLimit (New-TimeSpan -Hours 1)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Force `
    -Description "Shashi Pallava daily social creatives" | Out-Null

Write-Output ""
Write-Output "Registered scheduled task '$TaskName'"
Write-Output "  Mode:      $mode"
Write-Output "  Runs:      daily at $Time"
Write-Output "  Command:   $python $arguments"
Write-Output "  Log file:  $(Join-Path $root 'state\daily_run.log')"
Write-Output ""
Write-Output "Test it now with:  Start-ScheduledTask -TaskName '$TaskName'"
Write-Output "Remove it with:    .\register_daily_task.ps1 -Remove"
