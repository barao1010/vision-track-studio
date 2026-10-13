# Vision Track Studio

Projeto independente para Windows, planejado como distribuição modificada do [OBS Studio](https://github.com/obsproject/obs-studio), com a mesma interface e funcionalidades, mas identidade Vision Track Studio.

## Estado

**Bootstrap iniciado; não é ainda um aplicativo compilado.** Este repositório contém a preparação, não contém ainda o código-fonte completo nem um instalador.

## Começar no Windows

1. Instale Git for Windows, Visual Studio com ferramentas C++, Windows SDK e CMake conforme [instruções oficiais de build do OBS](https://github.com/obsproject/obs-studio/wiki/Build-Instructions-For-Windows).
2. Execute em PowerShell: `powershell -ExecutionPolicy Bypass -File .\scripts\obter-obs.ps1`.
3. O script descarrega o OBS com submódulos e prepara a pasta `upstream-obs`.
4. Depois, com dependências instaladas, execute `cmake --preset windows-x64` e `cmake --build --preset windows-x64` dentro dessa pasta.

**Atenção:** esse build inicial é o OBS *sem alterações*. Só distribuir sob o nome Vision Track Studio após modificar corretamente marcas, nomes internos, instalador, diretórios, atalhos e verificar compatibilidade de plugins, mantendo arquivos de licença e avisos de copyright.

## Plano de trabalho

- [x] Repositório separado criado
- [x] Documentação e script inicial de obtenção da base oficial
- [ ] Incorporar o código-fonte completo do OBS em fork/importação versionada
- [ ] Aplicar identidade Vision Track Studio ao programa inteiro
- [ ] Isolar configurações e atualizar instalador do Windows
- [ ] Compilar e testar áudio, vídeo, cenas, browsers, plugins e transmissão
- [ ] Publicar release e código-fonte correspondente sob os termos GPL

## Licença e atribuições

OBS Studio é software livre licenciado sob GPL-2.0-ou-posterior. Este repositório de preparação não é patrocinado pelo OBS Project e não altera sua marca oficial. Não retirar avisos de autoria/licença e preservar as licenças dos componentes de terceiros. Consulte https://github.com/obsproject/obs-studio/blob/master/COPYING .
