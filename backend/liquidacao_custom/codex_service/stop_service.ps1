param(
    [Parameter(Mandatory=$true)][string]$ServiceRoot,
    [string]$Executable = '',
    [switch]$RemoveTask
)
$ErrorActionPreference = 'Stop'
$env:PSModulePath = Join-Path $PSHOME 'Modules'
$root = [IO.Path]::GetFullPath($ServiceRoot).TrimEnd('\')
$expectedHost = Join-Path $root 'shared_host.py'
$task = Get-ScheduledTask -TaskName 'CalculosJuridicosMCP' -ErrorAction SilentlyContinue
if ($task) {
    $owned = @($task.Actions | Where-Object { $_.Execute -and $_.Execute.StartsWith(($root + '\'), [StringComparison]::OrdinalIgnoreCase) })
    if ($owned.Count -eq 0) { throw 'A tarefa existente pertence a outra instalação.' }
    Stop-ScheduledTask -TaskName 'CalculosJuridicosMCP'
}
$processes = @(Get-CimInstance Win32_Process)
$hostPattern = [regex]::Escape($expectedHost)
$ownedProcesses = @($processes | Where-Object {
    $_.Name -in @('python.exe','pythonw.exe') -and $_.ExecutablePath -and
    $_.ExecutablePath.StartsWith(($root + '\'), [StringComparison]::OrdinalIgnoreCase) -and
    $_.CommandLine -match $hostPattern
})
foreach ($ownedProcess in $ownedProcesses) {
    $stopping = Stop-Process -Id $ownedProcess.ProcessId -Force -PassThru -ErrorAction SilentlyContinue
    if ($stopping -and -not $stopping.WaitForExit(15000)) {
        throw 'O serviço anterior ainda está encerrando.'
    }
}
if ($Executable) {
    $expectedExecutable = [IO.Path]::GetFullPath($Executable)
    $legacy = @($processes | Where-Object {
        $_.Name -eq 'CalculosJuridicos.exe' -and $_.ExecutablePath -eq $expectedExecutable -and
        $_.CommandLine -match '(?:^|\s)--mcp(?:\s|$)'
    })
    foreach ($legacyProcess in $legacy) {
        $stopping = Stop-Process -Id $legacyProcess.ProcessId -Force -PassThru -ErrorAction SilentlyContinue
        if ($stopping -and -not $stopping.WaitForExit(15000)) {
            throw 'O conector anterior ainda está encerrando.'
        }
    }
}
if ($RemoveTask -and $task) {
    Unregister-ScheduledTask -TaskName 'CalculosJuridicosMCP' -Confirm:$false
}
