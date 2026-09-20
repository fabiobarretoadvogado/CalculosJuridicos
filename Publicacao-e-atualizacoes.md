# Publicação e atualizações

O Cálculos Jurídicos usa o mesmo modelo do OCR+MD: um instalador do Windows é publicado em **Releases** no GitHub e cada computador instalado consulta esse canal. O código-fonte e os dados de trabalho não são enviados pelo publicador.

## Primeira preparação desta máquina

1. Entre no GitHub pelo navegador e crie o repositório público `CalculosJuridicos`.
2. Entre também no GitHub CLI incluído em `.tools`:

```powershell
.\.tools\GitHubCLI\bin\gh.exe auth login
```

3. Instale as dependências do projeto uma única vez:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
cd ..
```

## Publicar a primeira versão

```powershell
.\publicar.ps1 -Repositorio fabiobarretoadvogado/CalculosJuridicos -Versao 1.00
```

O comando executa os testes, compila a interface, gera o programa, cria o instalador, assina o manifesto e publica exatamente três arquivos na Release:

- `CalculosJuridicos-Setup-<versão interna>-x64.exe`
- o arquivo `.sha256` correspondente;
- `update.json`, assinado digitalmente.

Uma cópia amigável do instalador fica em `instaladores\1.00`.

## Publicar uma atualização

Altere o projeto, valide as mudanças e escolha a próxima edição:

```powershell
.\publicar.ps1 -Versao 1.06
```

Os outros computadores verão a nova edição no rodapé do aplicativo. O download só é aceito se o manifesto, o nome, o tamanho e o SHA-256 do instalador corresponderem à assinatura.

## Preparar sem enviar

```powershell
.\publicar.ps1 -Repositorio fabiobarretoadvogado/CalculosJuridicos -Versao 1.00 -Preparar
```

Esse modo gera e confere todos os arquivos localmente, mas não cria uma Release.

## Chave de publicação

A chave privada fica protegida pelo Windows em `%LOCALAPPDATA%\CalculosJuridicos-Publisher` e nunca entra no projeto nem no instalador. Faça um backup criptografado e guarde a senha separadamente:

```powershell
.\backend\.venv\Scripts\python.exe .\scripts\publisher.py export-key --output D:\Backup\calculos-juridicos-chave.pem
```

Em outra máquina de publicação, restaure a mesma chave:

```powershell
.\backend\.venv\Scripts\python.exe .\scripts\publisher.py import-key --input D:\Backup\calculos-juridicos-chave.pem
```

Não gere outra chave depois de distribuir a primeira versão: os programas instalados confiam permanentemente na chave pública original.
