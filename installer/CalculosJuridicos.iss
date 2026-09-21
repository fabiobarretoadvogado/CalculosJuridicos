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

[Icons]
Name: "{autoprograms}\Cálculos Jurídicos"; Filename: "{app}\CalculosJuridicos.exe"; IconFilename: "{app}\_internal\liquidacao_custom\assets\calculos-juridicos.ico"; AppUserModelID: "CalculosJuridicos.{#AppIdValue}"; WorkingDir: "{userdocs}"
Name: "{autodesktop}\Cálculos Jurídicos"; Filename: "{app}\CalculosJuridicos.exe"; IconFilename: "{app}\_internal\liquidacao_custom\assets\calculos-juridicos.ico"; AppUserModelID: "CalculosJuridicos.{#AppIdValue}"; WorkingDir: "{userdocs}"; Tasks: desktopicon

[Run]
Filename: "{app}\CalculosJuridicos.exe"; Parameters: "--install-codex-plugin"; StatusMsg: "Configurando a integração com o Codex..."; Flags: runhidden waituntilterminated; Tasks: codexintegration
Filename: "{app}\CalculosJuridicos.exe"; Description: "Abrir Cálculos Jurídicos"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{app}\CalculosJuridicos.exe"; Parameters: "--uninstall-codex-plugin"; Flags: runhidden waituntilterminated; RunOnceId: "RemoveCodexIntegration"
