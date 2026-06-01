#!/usr/bin/env python3
"""
ZapFlow — importar_xlsx.py
Converte o XLSX da campanha em contatos.db (SQLite).

Uso:
    python3 importar_xlsx.py <nome_da_campanha>

Exemplo:
    python3 importar_xlsx.py minha_campanha

O arquivo XLSX deve estar em:
    campanhas/<nome_da_campanha>/contatos.xlsx

O banco gerado ficará em:
    campanhas/<nome_da_campanha>/contatos.db
"""

import sys
import os
import re
import sqlite3
import pandas as pd

# ─── Normalização de telefone ─────────────────────────────────────────────────
def normalizar_telefone(valor) -> str:
    """
    Aceita qualquer formato e retorna 5521999999999 (Evolution API).
    Exemplos tratados:
      (21) 99999-9999      → 5521999999999
      21999999999          → 5521999999999
      +55 21 9 9999-9999   → 5521999999999
      55219999999          → 5521999999999  (8 dígitos locais → não altera)
    Retorna vazio se não conseguir montar um número válido.
    """
    if valor is None:
        return ""

    # Remove tudo que não for dígito
    numero = re.sub(r"\D", "", str(valor))

    if not numero:
        return ""

    # Remove DDI 55 duplicado no início (ex: 5555...)
    if numero.startswith("55") and len(numero) > 13:
        numero = numero[2:]

    # Adiciona DDI 55 se não tiver
    if not numero.startswith("55"):
        numero = "55" + numero

    # Garante o 9 na frente do número local (celular BR com 9 dígitos)
    # Formato esperado: 55 + DDD(2) + 9(1) + numero(8) = 13 dígitos
    # Se tiver 12 dígitos: 55 + DDD(2) + numero(8) → insere o 9
    if len(numero) == 12:
        numero = numero[:4] + "9" + numero[4:]

    # Valida tamanho final
    if len(numero) != 13:
        return str(valor)   # devolve original se não conseguiu normalizar

    return numero

def importar(campanha: str):
    base_dir  = os.path.join(os.path.dirname(__file__), "campanhas", campanha)
    xlsx_path = os.path.join(base_dir, "contatos.xlsx")
    db_path   = os.path.join(base_dir, "contatos.db")

    if not os.path.isdir(base_dir):
        print(f"❌ Pasta da campanha não encontrada: {base_dir}")
        sys.exit(1)

    if not os.path.isfile(xlsx_path):
        print(f"❌ Arquivo não encontrado: {xlsx_path}")
        sys.exit(1)

    print(f"📂 Campanha  : {campanha}")
    print(f"📄 XLSX      : {xlsx_path}")
    print(f"🗄️  Banco     : {db_path}")
    print()

    # ── Lê o XLSX ────────────────────────────────────────────────────────────
    try:
        df = pd.read_excel(xlsx_path, engine="openpyxl")
    except Exception as e:
        print(f"❌ Erro ao ler o XLSX: {e}")
        sys.exit(1)

    # Limpa nomes de colunas (sem espaços, minúsculas)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    print(f"✅ {len(df)} linhas encontradas")
    print(f"📋 Colunas   : {list(df.columns)}")

    # ── Normaliza coluna de telefone ──────────────────────────────────────────
    col_fone = None
    for candidato in ["celular", "telefone", "whatsapp", "fone", "phone"]:
        if candidato in df.columns:
            col_fone = candidato
            break

    if col_fone:
        antes = df[col_fone].tolist()
        df[col_fone] = df[col_fone].apply(normalizar_telefone)
        depois = df[col_fone].tolist()
        invalidos = [str(a) for a, d in zip(antes, depois) if d == str(a) and len(re.sub(r"\D","",str(a))) not in (12,13)]
        print(f"📱 Coluna '{col_fone}' normalizada para formato Evolution API (5521999999999)")
        if invalidos:
            print(f"   ⚠️  {len(invalidos)} número(s) não puderam ser normalizados:")
            for n in invalidos[:5]:
                print(f"      {n}")
            if len(invalidos) > 5:
                print(f"      ... e mais {len(invalidos)-5}")
    else:
        print("   ⚠️  Nenhuma coluna de telefone encontrada (celular/telefone/whatsapp)")

    print()

    # ── Salva no SQLite ───────────────────────────────────────────────────────
    conn = sqlite3.connect(db_path)
    df.to_sql("contatos", conn, if_exists="replace", index_label="id")
    conn.close()

    print(f"✅ Banco criado/atualizado com sucesso: {db_path}")
    print()
    print("💡 Variáveis disponíveis para mensagem.txt:")
    for col in df.columns:
        print(f"   {{{col}}}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 importar_xlsx.py <nome_da_campanha>")
        sys.exit(1)

    importar(sys.argv[1])
