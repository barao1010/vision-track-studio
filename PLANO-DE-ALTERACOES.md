# Plano de implementação — Vision Track Studio

Objetivo: manter os recursos do OBS e construir distribuição Windows independente com marca Vision Track Studio.

## Fase 1 — base e validação
- [x] Repositório próprio sem tocar no Vision Track AI
- [x] Script para recuperar upstream com submódulos
- [x] GitHub Actions para tentar compilar OBS original (resultado ainda não validado)
- [ ] Compilação concluída com sucesso em runner Windows

## Fase 2 — identidade real
- [ ] Alterar nomes visíveis na UI e traduções sem alterar avisos de autoria
- [ ] Alterar metadados de recursos, executável, instalador, ícones e atalhos
- [ ] Ajustar nomes de diretórios e perfil de configurações, garantindo migração e isolamento
- [ ] Fazer testes de plugins, navegador, fontes, codecs, virtual camera, transmissão e áudio

## Fase 3 — distribuição
- [ ] Incorporar fonte modificada completa em repositório versionado com submódulos e licenças
- [ ] Compilar e empacotar Vision Track Studio
- [ ] Publicar release de Windows e código-fonte correspondente conforme GPL
- [ ] Testar instalação lado a lado com OBS

A CI atual valida *apenas upstream sem rebranding*, e não produz instalador oficial Vision Track Studio. Não distribuir o artefato da CI como o produto final.
