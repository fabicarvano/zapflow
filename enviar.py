#!/usr/bin/env python3
"""
ZapFlow — enviar.py
Lê a campanha, monta mensagens com variáveis do banco e dispara via Evolution API.

Uso:
    python3 enviar.py <nome_da_campanha>

Exemplo:
    python3 enviar.py minha_campanha

Estrutura esperada da campanha:
    campanhas/<nome>/contatos.db    ← gerado pelo importar_xlsx.py
    campanhas/<nome>/mensagem.txt   ← texto com variáveis ex: {primeiro_nome}

Configuração global em .env na raiz do projeto.
"""

import sys
import os
import sqlite3
import requests
import time
from dotenv import load_dotenv

# ─── Carrega .env ─────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(__file__)
load_dotenv(os.path.join(BASE_DIR, ".env"))

EVOLUTION_URL   = os.getenv("EVOLUTION_URL", "http://localhost:8080")
API_KEY         = os.getenv("API_KEY", "")
INSTANCIA       = os.getenv("INSTANCIA", "default")
INTERVALO       = int(os.getenv("INTERVALO", "2"))
COLUNA_CELULAR  = os.getenv("COLUNA_CELULAR", "celular")

HEADERS = {
    "apikey": API_KEY,
    "Content-Type": "application/json",
}

# ─── Carrega arquivos da campanha ─────────────────────────────────────────────
def carregar_campanha(campanha: str):
    camp_dir = os.path.join(BASE_DIR, "campanhas", campanha)
    db_path  = os.path.join(camp_dir, "contatos.db")
    msg_path = os.path.join(camp_dir, "mensagem.txt")

    if not os.path.isdir(camp_dir):
        print(f"❌ Campanha não encontrada: {camp_dir}")
        sys.exit(1)

    if not os.path.isfile(db_path):
        print(f"❌ Banco não encontrado: {db_path}")
        print("   Rode primeiro: python3 importar_xlsx.py <campanha>")
        sys.exit(1)

    if not os.path.isfile(msg_path):
        print(f"❌ Mensagem não encontrada: {msg_path}")
        sys.exit(1)

    with open(msg_path, "r", encoding="utf-8") as f:
        template = f.read()

    return db_path, template

# ─── Lê contatos do banco ─────────────────────────────────────────────────────
def carregar_contatos(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row          # permite acessar colunas por nome
    cur  = conn.cursor()
    cur.execute(f"SELECT * FROM contatos WHERE {COLUNA_CELULAR} IS NOT NULL AND {COLUNA_CELULAR} != ''")
    contatos = cur.fetchall()
    conn.close()
    return contatos

# ─── Monta mensagem com variáveis do banco ────────────────────────────────────
def montar_mensagem(template: str, contato: sqlite3.Row) -> str:
    dados = dict(contato)
    try:
        return template.format_map(dados)
    except KeyError as e:
        print(f"   ⚠️  Variável {e} não encontrada no banco — verifique mensagem.txt")
        return template

# ─── Envia mensagem via Evolution API ────────────────────────────────────────
def enviar_mensagem(numero: str, mensagem: str):
    url     = f"{EVOLUTION_URL}/message/sendText/{INSTANCIA}"
    payload = {"number": numero, "text": mensagem}
    resp    = requests.post(url, headers=HEADERS, json=payload, timeout=15)
    return resp.status_code, resp.text

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("Uso: python3 enviar.py <nome_da_campanha>")
        sys.exit(1)

    campanha = sys.argv[1]
    db_path, template = carregar_campanha(campanha)
    contatos = carregar_contatos(db_path)

    total   = len(contatos)
    enviado = 0
    falhou  = 0

    print(f"\n🚀 ZapFlow — Campanha: {campanha}")
    print(f"   Instância  : {INSTANCIA}")
    print(f"   Contatos   : {total}")
    print(f"   Intervalo  : {INTERVALO}s entre envios")
    print("─" * 50)

    for contato in contatos:
        dados   = dict(contato)
        numero  = str(dados.get(COLUNA_CELULAR, "")).strip()
        nome    = dados.get("primeiro_nome") or dados.get("nome") or numero
        msg     = montar_mensagem(template, contato)

        status, body = enviar_mensagem(numero, msg)

        if status in (200, 201):
            print(f"  ✅ {nome} ({numero}) — enviado")
            enviado += 1
        else:
            print(f"  ❌ {nome} ({numero}) — erro {status}: {body[:120]}")
            falhou += 1

        time.sleep(INTERVALO)

    print("─" * 50)
    print(f"  Total      : {total}")
    print(f"  Enviados   : {enviado}")
    print(f"  Falhas     : {falhou}")
    print()

if __name__ == "__main__":
    main()
