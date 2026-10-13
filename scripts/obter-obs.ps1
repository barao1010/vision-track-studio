param([string]$Destination = "upstream-obs", [string]$Ref = "master")
$ErrorActionPreference = "Stop"
if (Test-Path $Destination) { throw "Destino ja existe: $Destination. Nenhum arquivo foi substituido." }
& git clone --recursive https://github.com/obsproject/obs-studio.git $Destination
if ($LASTEXITCODE -ne 0) { throw "Falha ao clonar OBS." }
Push-Location $Destination
try {
  & git checkout $Ref
  if ($LASTEXITCODE -ne 0) { throw "Ref do OBS inexistente." }
  & git submodule update --init --recursive
  if ($LASTEXITCODE -ne 0) { throw "Falha ao obter submodulos." }
  Write-Host "Codigo-fonte original obtido. Ainda nao renomeado ou compilado." 
} finally { Pop-Location }
