🇧🇷 Português | 🇺🇸 [English](README.en.md)

# Limpador de Arquivos Temporários para Windows

Programa com interface gráfica para limpar arquivos temporários e caches no **Windows 10 e 11**, feito em Python (tkinter). Mostra quanto espaço será liberado **antes** de apagar qualquer coisa.


## O que ele limpa?

| Categoria | Marcada por padrão |
|---|---|
| Temporários do usuário | Sim |
| Temporários do Windows | Sim |
| Cache do Windows Update | Sim |
| Relatórios de erro (CrashDumps) | Sim |
| Cache do Edge, Chrome e Brave (todos os perfis) | Sim |
| Prefetch | Não |
| Logs do Windows | Não |
| Lixeira | Não |

## Recursos

- Simulação: mostra o tamanho de cada categoria antes de apagar
- Confirmação antes da limpeza
- Filtro por idade: apaga só arquivos com mais de X dias (padrão: 1 dia)
- Aviso quando um navegador está aberto
- Barra de progresso e área de log
- Log salvo em `limpador_log.txt`, ao lado do programa

## Como instalar e usar

### Opção 1: baixar o programa (recomendado)

1. Acesse a aba [**Releases**](../../releases) deste repositório.
2. Baixe o arquivo `arquivos_temporarios_windows.exe`
3. Dê dois cliques e permita a execução como Administrador.
4. Clique em **Analisar de novo**, marque o que deseja e clique em **Limpar selecionados**.

> O Windows SmartScreen ou o antivírus pode mostrar um alerta, porque o programa **não tem assinatura digital**. O código-fonte completo está neste repositório e pode ser conferido. Se preferir, rode a partir do código (opção 2).

### Opção 2: rodar a partir do código

Requisitos: Windows 10/11 e [Python 3.8+](https://www.python.org/downloads/) (o tkinter já vem com o instalador oficial).

```
python arquivos_temporarios_windows.py
```

Para abrir sem a janela do terminal, renomeie para `arquivos_temporarios_windows.pyw` e dê dois cliques.

### Gerar o seu próprio .exe

```
pip install pyinstaller
pyinstaller --onefile --noconsole --uac-admin arquivos_temporarios_windows.py
```

O arquivo será criado na pasta `dist`

## Avisos importantes

- **A exclusão é permanente.** Confira a lista antes de confirmar.
- Feche os navegadores antes de limpar o cache, senão parte dele não será apagada.
- Evite limpar com instalações ou atualizações do Windows em andamento.
- **Prefetch** e **Logs do Windows** ficam desmarcados por padrão: liberam pouco espaço e têm efeitos colaterais (programas abrem mais lentos por um tempo e menos registros para diagnóstico).
- Se quiser, crie um ponto de restauração do Windows antes de usar.
- Este software é fornecido **sem garantias**, conforme a licença MIT. Use por sua conta e risco.

## Encontrou um problema?

Abra uma [Issue](../../issues) informando a versão do Windows, o que aconteceu e, se houver, a mensagem de erro ou o conteúdo do `limpador_log.txt`

## Licença

Distribuído sob a licença MIT. Veja o arquivo [LICENSE](LICENSE).
