param([Parameter(Mandatory=$true)][string]$JobFile)
$env:PSModulePath = Join-Path $PSHOME 'Modules'
Import-Module (Join-Path $PSHOME 'Modules\Microsoft.PowerShell.Utility\Microsoft.PowerShell.Utility.psd1') -Force
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$taskDirectory = Split-Path -Parent ([IO.Path]::GetFullPath($JobFile))
$taskCache = [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'CalculosJuridicos\updates')).TrimEnd('\') + '\'
$taskResult = [ordered]@{ Success=$false; Version=$null; ExitCode=$null; Error=$null }
$taskExecutable = $null
$taskJob = $null
$taskDirectoryAccepted = $false
try {
    if (-not ($taskDirectory + '\').StartsWith($taskCache, [StringComparison]::OrdinalIgnoreCase)) { throw 'Pasta de atualização fora do local permitido.' }
    $taskDirectoryAccepted = $true
    $taskJob = Get-Content -LiteralPath $JobFile -Raw -Encoding UTF8 | ConvertFrom-Json
    $taskResult.Version = $taskJob.Version
    if ($taskJob.AppId -ne '7d3d1b6f-7c56-4f0e-8a63-1aa1dc62c5f4' -or $taskJob.Executable -ne 'CalculosJuridicos.exe') { throw 'Identidade do aplicativo inválida.' }
    $taskInstaller = (Resolve-Path -LiteralPath $taskJob.Installer).Path
    if ((Split-Path -Parent $taskInstaller) -ne $taskDirectory -or (Get-Item -LiteralPath $taskInstaller).Attributes.HasFlag([IO.FileAttributes]::ReparsePoint)) { throw 'Instalador fora da pasta da atualização.' }
    $taskInstallDir = (Resolve-Path -LiteralPath $taskJob.InstallDir).Path.TrimEnd('\')
    if ($taskInstallDir -match '["\r\n]' -or $taskInstallDir -eq [IO.Path]::GetPathRoot($taskInstallDir).TrimEnd('\')) { throw 'Pasta de instalação inválida.' }
    $taskRegistration = Get-ItemProperty -LiteralPath ('HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\' + $taskJob.AppId + '_is1')
    if ([IO.Path]::GetFullPath($taskRegistration.InstallLocation).TrimEnd('\') -ne $taskInstallDir) { throw 'A pasta difere da instalação registrada.' }
    $taskExecutable = Join-Path $taskInstallDir $taskJob.Executable
    $taskIdentity = Get-Content -LiteralPath (Join-Path $taskInstallDir 'app-info.json') -Raw | ConvertFrom-Json
    if ($taskIdentity.app_id -ne $taskJob.AppId) { throw 'Aplicativo de destino diferente.' }
    if ($taskJob.ParentPID -gt 0) {
        $taskParent = Get-Process -Id $taskJob.ParentPID -ErrorAction SilentlyContinue
        if ($taskParent -and -not $taskParent.WaitForExit(120000)) { throw 'O aplicativo ainda está aberto. Atualização adiada.' }
    }
    $taskOtherInstances = @(Get-CimInstance Win32_Process -Filter "Name='CalculosJuridicos.exe'" | Where-Object { $_.ExecutablePath -eq $taskExecutable })
    if ($taskOtherInstances.Count -gt 0) { throw 'Feche as outras janelas de Cálculos Jurídicos e tente atualizar novamente.' }
    if ((Get-Item -LiteralPath $taskInstaller).Length -ne $taskJob.Size -or (Get-FileHash -LiteralPath $taskInstaller -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskJob.SHA256) { throw 'O instalador não passou na verificação de integridade.' }
    $taskArguments = @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/NOCLOSEAPPLICATIONS','/NORESTARTAPPLICATIONS',('/DIR="' + $taskInstallDir + '"'),('/LOG="' + (Join-Path $taskDirectory 'instalacao.log') + '"'))
    $taskSetup = Start-Process -FilePath $taskInstaller -ArgumentList $taskArguments -WindowStyle Hidden -PassThru
    if (-not $taskSetup.WaitForExit(600000)) { throw 'O instalador ainda está em execução. Consulte o registro da instalação.' }
    $taskSetup.Refresh()
    $taskResult.ExitCode = $taskSetup.ExitCode
    if ($taskSetup.ExitCode -ne 0) { throw ('O instalador retornou o código ' + $taskSetup.ExitCode + '. Consulte instalacao.log.') }
    if ((Get-Item -LiteralPath $taskExecutable).VersionInfo.FileVersion -ne $taskJob.Version) { throw 'A versão instalada difere da esperada.' }
    $taskResult.Success = $true
    $env:PYINSTALLER_RESET_ENVIRONMENT = '1'
    if ($taskJob.Restart) { Start-Process -FilePath $taskExecutable -WorkingDirectory ([Environment]::GetFolderPath('MyDocuments')) | Out-Null }
}
catch {
    $taskResult.Error = $_.Exception.Message
    $env:PYINSTALLER_RESET_ENVIRONMENT = '1'
    if ($taskExecutable -and (Test-Path -LiteralPath $taskExecutable) -and $taskJob -and $taskJob.Restart) { Start-Process -FilePath $taskExecutable | Out-Null }
    if ($taskJob -and $taskJob.Restart) {
        try { $taskNotice = New-Object -ComObject WScript.Shell; $taskNotice.Popup(('A atualização não foi concluída. ' + $taskResult.Error), 30, 'Cálculos Jurídicos', 48) | Out-Null } catch {}
    }
}
finally {
    if ($taskDirectoryAccepted) { $taskResult | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $taskDirectory 'resultado.json') -Encoding UTF8 }
}
if (-not $taskResult.Success) { exit 1 }

