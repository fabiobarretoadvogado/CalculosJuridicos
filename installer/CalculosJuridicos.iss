#ifndef AppVersion
  #error AppVersion must be supplied by build-installer.ps1
#endif
#ifndef AppDisplayVersion
  #define AppDisplayVersion AppVersion
#endif
#ifndef AppIdValue
  #error AppIdValue must be supplied by build-installer.ps1
#endif
#ifndef PayloadDir
  #error PayloadDir must be supplied by build-installer.ps1
#endif
#ifndef InstallerOutput
  #error InstallerOutput must be supplied by build-installer.ps1
#endif

[Setup]
AppId={#AppIdValue}
AppName=Cálculos Jurídicos
AppVersion={#AppDisplayVersion}
AppVerName=Cálculos Jurídicos {#AppDisplayVersion}
DefaultDirName={localappdata}\Programs\CalculosJuridicos
DefaultGroupName=Cálculos Jurídicos
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible and not arm64
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
OutputDir={#InstallerOutput}
OutputBaseFilename=CalculosJuridicos-Setup-{#AppVersion}-x64
VersionInfoVersion={#AppVersion}
VersionInfoProductVersion={#AppVersion}
VersionInfoProductTextVersion={#AppDisplayVersion}
VersionInfoDescription=Instalador do Cálculos Jurídicos
VersionInfoProductName=Cálculos Jurídicos
UninstallDisplayName=Cálculos Jurídicos
SetupIconFile={#PayloadDir}\_internal\liquidacao_custom\assets\calculos-juridicos.ico
UninstallDisplayIcon={app}\_internal\liquidacao_custom\assets\calculos-juridicos.ico
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
UsePreviousAppDir=yes
UsePreviousTasks=yes
SetupLogging=yes

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked
Name: "codexintegration"; Description: "Integrar ao Codex para fazer cálculos e gerar PDFs sem abrir o programa"; GroupDescription: "Integrações:"

[Files]
Source: "{#PayloadDir}\CalculosJuridicos.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#PayloadDir}\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#PayloadDir}\app-info.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#PayloadDir}\LEIA-ME.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#PayloadDir}\codex-service\*"; DestDir: "{app}\codex-service"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#PayloadDir}\codex-service\stop_service.ps1"; DestDir: "{tmp}"; DestName: "stop-codex-before-install.ps1"; Flags: dontcopy

[Icons]
Name: "{autoprograms}\Cálculos Jurídicos"; Filename: "{app}\CalculosJuridicos.exe"; IconFilename: "{app}\_internal\liquidacao_custom\assets\calculos-juridicos.ico"; AppUserModelID: "CalculosJuridicos.{#AppIdValue}"; WorkingDir: "{userdocs}"
Name: "{autodesktop}\Cálculos Jurídicos"; Filename: "{app}\CalculosJuridicos.exe"; IconFilename: "{app}\_internal\liquidacao_custom\assets\calculos-juridicos.ico"; AppUserModelID: "CalculosJuridicos.{#AppIdValue}"; WorkingDir: "{userdocs}"; Tasks: desktopicon

[Run]
Filename: "{app}\codex-service\runtime\pythonw.exe"; Parameters: "-E -s ""{app}\codex-service\manage.py"" install --executable ""{app}\CalculosJuridicos.exe"""; StatusMsg: "Configurando o serviço compartilhado do Codex..."; Flags: runhidden waituntilterminated; Tasks: codexintegration; AfterInstall: CheckCodexIntegration
Filename: "{app}\codex-service\runtime\pythonw.exe"; Parameters: "-E -s ""{app}\codex-service\manage.py"" uninstall --executable ""{app}\CalculosJuridicos.exe"""; StatusMsg: "Removendo a integração anterior com o Codex..."; Flags: runhidden waituntilterminated; Check: ShouldRemoveIntegration
Filename: "{app}\CalculosJuridicos.exe"; Description: "Abrir Cálculos Jurídicos"; Flags: nowait postinstall skipifsilent unchecked

[UninstallRun]
Filename: "{app}\codex-service\runtime\pythonw.exe"; Parameters: "-E -s ""{app}\codex-service\manage.py"" uninstall --executable ""{app}\CalculosJuridicos.exe"""; Flags: runhidden waituntilterminated skipifdoesntexist; RunOnceId: "RemoveCodexIntegration"

[Code]
function SharedServiceRoot: String;
begin
  Result := GetEnv('USERPROFILE') + '\.codex\integrations\calculos-juridicos';
end;

function ShouldRemoveIntegration: Boolean;
begin
  Result := (not WizardIsTaskSelected('codexintegration')) and
    (FileExists(SharedServiceRoot + '\settings.json') or
    FileExists(GetEnv('USERPROFILE') + '\plugins\calculos-juridicos\.managed-by-calculos-juridicos.json'));
end;

procedure CheckCodexIntegration;
var
  ResultCode: Integer;
  Parameters: String;
begin
  Parameters := '-E -s "' + ExpandConstant('{app}\codex-service\manage.py') +
    '" check --executable "' + ExpandConstant('{app}\CalculosJuridicos.exe') + '"';
  if not Exec(ExpandConstant('{app}\codex-service\runtime\pythonw.exe'),
    Parameters, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    RaiseException('Não foi possível verificar a integração com o Codex.')
  else if ResultCode <> 0 then
    RaiseException('O serviço do Codex não ficou disponível. Consulte installation.log na pasta da integração.');
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
  Parameters: String;
begin
  Result := '';
  ExtractTemporaryFile('stop-codex-before-install.ps1');
  Parameters := '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' +
    ExpandConstant('{tmp}\stop-codex-before-install.ps1') +
    '" -ServiceRoot "' + SharedServiceRoot +
    '" -Executable "' + ExpandConstant('{app}\CalculosJuridicos.exe') + '"';
  if not Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
    Parameters, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    Result := 'Não foi possível preparar o serviço do Codex para a atualização.'
  else if ResultCode <> 0 then
    Result := 'Não foi possível encerrar o serviço anterior do Codex. Consulte o registro da instalação.';
end;

