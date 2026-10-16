; GPL-2.0-or-later
[Setup]
AppId=VisionTrackStudioPreview
AppName=Vision Track Studio
AppVersion=0.1.0-preview
DefaultDirName={autopf}\Vision Track Studio
DefaultGroupName=Vision Track Studio
OutputDir=..\..
OutputBaseFilename=Vision-Track-Studio-Setup-preview
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
CloseApplications=yes
RestartApplications=yes
LicenseFile=..\..\obs-studio\COPYING
SetupIconFile=..\..\obs-studio\frontend\cmake\windows\obs-studio.ico
[Files]
Source: "..\..\obs-studio\build_x64\rundir\RelWithDebInfo\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\Vision Track Studio"; Filename: "{app}\bin\64bit\vision-track-studio.exe"; WorkingDir: "{app}\bin\64bit"
Name: "{autodesktop}\Vision Track Studio"; Filename: "{app}\bin\64bit\vision-track-studio.exe"; WorkingDir: "{app}\bin\64bit"
