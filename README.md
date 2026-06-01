# ZapFlow 🟢
Disparo de mensagens WhatsApp via Evolution API — multi-campanha, configurável por `.env`.

---

## Estrutura

```
zapflow/
├── .env                          ← configuração global (API, instância, intervalo)
├── importar_xlsx.py              ← converte XLSX → SQLite
├── enviar.py                     ← envia mensagens da campanha
├── setup_cron.sh                 ← agenda envio via crontab
└── campanhas/
    └── nome_da_campanha/
        ├── contatos.xlsx         ← você coloca aqui
        ├── mensagem.txt          ← texto com variáveis {coluna}
        ├── contatos.db           ← gerado automaticamente
        └── envio.log             ← gerado pelo cron
```

---

## Passo a passo

### 1. Configure o `.env`
```env
EVOLUTION_URL=http://SEU_IP:8080
API_KEY=SUA_CHAVE
INSTANCIA=NOME_DA_INSTANCIA
INTERVALO=2
COLUNA_CELULAR=celular
```

### 2. Crie a pasta da campanha
```bash
mkdir campanhas/minha_campanha
```

### 3. Coloque o XLSX na pasta
O arquivo deve ter cabeçalho na primeira linha. Exemplo:

| primeiro_nome | empresa | cargo | celular |
|---|---|---|---|
| João | Petrobras | Gerente | 5521999... |

### 4. Escreva a mensagem
Edite `campanhas/minha_campanha/mensagem.txt` usando `{nome_da_coluna}`:

```
Fala, {primeiro_nome}!

Vi que você é {cargo} na {empresa} e queria te convidar...

Abraço,
Fabio Carvano | Decatron
```

### 5. Importe o XLSX
```bash
python3 importar_xlsx.py minha_campanha
```
O script lista todas as variáveis disponíveis ao final.

### 6. Dispare
```bash
python3 enviar.py minha_campanha
```

### 7. (Opcional) Agende via cron
```bash
bash setup_cron.sh minha_campanha 10 00   # roda todo dia às 10h
```

---

## Dependências
```bash
pip install pandas openpyxl requests python-dotenv
```
