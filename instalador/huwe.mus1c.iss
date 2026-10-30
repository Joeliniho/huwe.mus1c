; Inno Setup: crea «huwe.mus1c-setup-<versión>.exe».
; Antes: empaquetar con PyInstaller (ver huwe.mus1c.spec). Compilar: ISCC.exe instalador\huwe.mus1c.iss

#define AppName "huwe.mus1c"
#define AppVersion "0.3"
#define AppExe "huwe.mus1c.exe"

[Setup]
AppId={{620B37EE-A65C-4DE4-A594-231A3CC0123F}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Huwe
AppComments=Free all-in-one audio studio: live guitar amp, mastering, voice cleanup, audio to tab.
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
OutputDir=salida
OutputBaseFilename=huwe.mus1c-setup-{#AppVersion}
SetupIconFile=..\icono.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2/max
SolidCompression=yes
LZMAUseSeparateProcess=yes
LZMANumBlockThreads=2
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
; también se puede instalar solo para el usuario (sin permisos de admin; entonces no instala el plugin VST3)
PrivilegesRequiredOverridesAllowed=dialog commandline
ShowLanguageDialog=auto

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[CustomMessages]
english.TaskTone=Install the TONE3000 amp plugin (free, open source, MIT)
spanish.TaskTone=Instalar el plugin de amplis TONE3000 (gratis, código abierto, MIT)
english.TaskNam=Open the NAM Rig download page (free amp sim, installed from its official site)
spanish.TaskNam=Abrir la web para descargar NAM Rig (ampli gratis, se instala desde su web oficial)
english.GroupAmps=Free amp sims:
spanish.GroupAmps=Amplis gratis:
english.Launch=Open huwe.mus1c
spanish.Launch=Abrir huwe.mus1c

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "tone3000"; Description: "{cm:TaskTone}"; GroupDescription: "{cm:GroupAmps}"; Check: not ToneInstalado
Name: "namrig"; Description: "{cm:TaskNam}"; GroupDescription: "{cm:GroupAmps}"; Check: not NamInstalado

[Files]
Source: "dist\huwe.mus1c\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "terceros\TONE3000-LICENSE.txt"; DestDir: "{app}\licenses"; Flags: ignoreversion
; El plugin va a la carpeta estándar de VST3 para que lo vean también Reaper y otros programas.
Source: "terceros\TONE3000.vst3\*"; DestDir: "{commoncf64}\VST3\TONE3000.vst3"; Tasks: tone3000; \
  Flags: ignoreversion recursesubdirs createallsubdirs uninsneveruninstall

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "https://www.tone3000.com/blog/jordan-valeriote-nam-rig"; Tasks: namrig; Flags: shellexec nowait skipifsilent
Filename: "{app}\{#AppExe}"; Description: "{cm:Launch}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
function ToneInstalado: Boolean;
begin
  { sin admin no se puede escribir en la carpeta común de VST3: se oculta la opción }
  Result := (not IsAdminInstallMode) or DirExists(ExpandConstant('{commoncf64}\VST3\TONE3000.vst3'));
end;

function NamInstalado: Boolean;
begin
  Result := DirExists(ExpandConstant('{commoncf64}\VST3\NAM Rig.vst3'));
end;
