param([Parameter(Mandatory=$true)][string]$ServiceRoot)
$ErrorActionPreference = 'Stop'
$env:PSModulePath = Join-Path $PSHOME 'Modules'
$root = [IO.Path]::GetFullPath($ServiceRoot)
$pythonWindowed = Join-Path $root 'runtime\pythonw.exe'
$hostScript = Join-Path $root 'shared_host.py'
if (-not (Test-Path -LiteralPath $pythonWindowed) -or -not (Test-Path -LiteralPath $hostScript)) {
    throw 'O ambiente do serviço não está completo.'
}
$existing = Get-ScheduledTask -TaskName 'CalculosJuridicosMCP' -ErrorAction SilentlyContinue
if ($existing) {
    $owned = @($existing.Actions | Where-Object { $_.Execute -eq $pythonWindowed })
    if ($owned.Count -eq 0) { throw 'A tarefa existente pertence a outra instalação.' }
}
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$action = New-ScheduledTaskAction -Execute $pythonWindowed -Argument ('-E -s -X utf8 "' + $hostScript + '"') -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $identity.Name
$principal = New-ScheduledTaskPrincipal -UserId $identity.Name -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew -RestartCount 10 -RestartInterval (New-TimeSpan -Minutes 1) -Hidden
Register-ScheduledTask -TaskName 'CalculosJuridicosMCP' -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'Servidor local único para os cálculos do Codex, sem cópias por chat.' -Force | Out-Null
Start-ScheduledTask -TaskName 'CalculosJuridicosMCP'
