[Setup]
AppId=VisionTrackStudioIndependentDev
AppName=Vision Track Studio - Desenvolvimento
AppVersion=0.2.0.3
AppPublisher=Vision Track Studio
DefaultDirName={localappdata}\VisionTrackStudioDev
DefaultGroupName=Vision Track Studio - Desenvolvimento
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=Vision-Track-Studio-0.2.0-dev.3-Setup
SetupIconFile=..\assets\vision-track.ico
UninstallDisplayIcon={app}\VisionTrackStudio.exe
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
[Files]
Source: "..\dist\VisionTrackStudio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\Vision Track Studio"; Filename: "{app}\VisionTrackStudio.exe"
Name: "{group}\Manual"; Filename: "{app}\docs\Vision-Track-Studio-Manual-PT.pdf"
