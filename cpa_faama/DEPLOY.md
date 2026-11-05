# Publicação do sistema da CPA

O sistema precisa rodar num **servidor sempre ligado**, com **HTTPS** e acesso à API do TOTVS RM.
Não publique em serviços gratuitos públicos nem use "Publicar na Web" do Power BI: os dados ficariam abertos.

## O que pedir à TI

1. Um servidor (Linux com Docker, recomendado, ou Windows Server).
2. Um endereço, por exemplo `cpa.faama.edu.br`, apontando para o servidor.
3. Liberação de saída do servidor para a API do RM (`institutoadventista160181.rm.cloudtotvs.com.br:8051`).
4. Um usuário do RM **só de leitura**, com acesso apenas às consultas FAAMACPA.6 e FAAMACPA.7.
5. Decidir se o site fica só na rede interna/VPN ou também acessível pela internet (com login obrigatório).

## Opção A: Linux com Docker (recomendada)

```bash
# no servidor, dentro da pasta do projeto
cp .env.example .env            # preencher URL, usuário e senha da API
python3 scripts/criar_usuario.py cpa --nome "CPA" --perfil admin   # ou rodar dentro do contêiner
# editar deploy/Caddyfile com o endereço definido pela TI
cd deploy && docker compose up -d
```

- O Caddy emite o certificado HTTPS automaticamente.
- `restart: always` faz o sistema voltar sozinho se o servidor reiniciar.
- Para atualizar o sistema: substituir os arquivos e rodar `docker compose up -d --build`.

## Opção B: Windows Server

1. Instalar Python 3.12 e criar o ambiente: `python -m venv .venv` e `pip install -r requirements.txt`.
2. Registrar o site como serviço do Windows com o NSSM (`nssm install CPA`), apontando para
   `.venv\Scripts\python.exe -m streamlit run app.py --server.port 8501 --server.address 127.0.0.1`.
3. No IIS, instalar **URL Rewrite** e **Application Request Routing**, ativar o proxy e criar uma regra
   de proxy reverso para `http://127.0.0.1:8501`, com **WebSocket** habilitado (o Streamlit depende disso).
4. Associar o certificado HTTPS ao site no IIS.

## Segurança já embutida no sistema

- Login obrigatório, senhas guardadas só como hash (bcrypt).
- Perfis: CPA, coordenador (só o próprio curso), professor (só o próprio resultado) e
  **avaliador externo** (somente leitura, sem nomes de professores nem comentários, com data de validade).
- Sessão encerrada após `SESSAO_MINUTOS` sem uso (padrão 60).
- Registro de acessos (login, páginas, saídas) na página Administração.
- Sigilo: grupos com menos de `MIN_RESPONDENTES` não são detalhados.

## Acesso para a visita do MEC

```bash
python scripts/criar_usuario.py mec.avaliador1 --nome "Comissão de Avaliação MEC" --perfil avaliador --validade 2026-12-15
```

O avaliador vê: Início, Visão Geral, Avaliação do Curso, Infraestrutura, Participação, Histórico,
Relatório da CPA (PDF) e Metodologia. O acesso deixa de funcionar sozinho após a data de validade.
Depois da visita, desative: `python scripts/criar_usuario.py mec.avaliador1 --desativar`.

## Cuidados

- `.env`, `config/` e `data/` nunca devem ser enviados por e-mail, chat ou repositório.
- Faça backup periódico de `config/` (usuários e moderação).
- A pasta `data/` pode ser apagada: o sistema baixa tudo de novo da API.
