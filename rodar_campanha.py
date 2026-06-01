
def enviar_campanha_completa(caminho_db, texto_base):
    import sqlite3
    import json
    import time
    import requests
    from datetime import datetime

    print()
    print("🚀 Iniciando envio da campanha completa")
    linha()

    conn = sqlite3.connect(caminho_db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM contatos WHERE COALESCE(enviado, 0) = 0 ORDER BY id")
    contatos = cur.fetchall()

    total = len(contatos)
    enviados = 0
    pulados = 0
    erros = 0

    headers = {
        "apikey": API_KEY,
        "Content-Type": "application/json"
    }

    for contato in contatos:
        contato_id = contato["id"]
        nome = contato["nome"] or ""
        sobrenome = contato["sobrenome"] or ""
        celular = str(contato[COLUNA_CELULAR] or "").strip()

        ja_enviado = 0
        if "enviado" in contato.keys():
            ja_enviado = contato["enviado"] or 0

        nome_exibicao = f"{nome} {sobrenome}".strip() or celular

        if ja_enviado == 1:
            print(f"⏭️ Pulando já enviado: {nome_exibicao} | {celular}")
            pulados += 1
            continue

        if not celular:
            print(f"❌ Sem celular: {nome_exibicao}")
            erros += 1
            marcar_contato_enviado(caminho_db, contato_id, "Número de celular vazio")
            continue

        mensagem = texto_base

        for chave in contato.keys():
            valor = "" if contato[chave] is None else str(contato[chave])
            mensagem = mensagem.replace("{" + chave + "}", valor)

        variaveis_pendentes = re.findall(r"{[^{}]+}", mensagem)
        if variaveis_pendentes:
            erro = "Variáveis não substituídas: " + ", ".join(variaveis_pendentes)
            print(f"❌ Erro para {nome_exibicao}: {erro}")
            erros += 1
            marcar_contato_enviado(caminho_db, contato_id, erro)
            continue

        payload = {
            "number": celular,
            "text": mensagem
        }

        try:
            url = f"{EVOLUTION_URL}/message/sendText/{INSTANCIA}"
            r = requests.post(url, headers=headers, json=payload, timeout=30)

            if 200 <= r.status_code < 300:
                marcar_contato_enviado(caminho_db, contato_id)
                enviados += 1
                print(f"✅ Enviado para: {nome_exibicao} | {celular}")
            else:
                erro = f"HTTP {r.status_code}: {r.text}"
                marcar_contato_enviado(caminho_db, contato_id, erro)
                erros += 1
                print(f"❌ Erro ao enviar para: {nome_exibicao} | {celular}")
                print(f"   {erro[:300]}")

        except Exception as e:
            erro = str(e)
            marcar_contato_enviado(caminho_db, contato_id, erro)
            erros += 1
            print(f"❌ Erro ao enviar para: {nome_exibicao} | {celular}")
            print(f"   {erro[:300]}")

        time.sleep(int(INTERVALO))

    conn.close()

    print()
    linha()
    print("📊 Resumo da campanha")
    print(f"Total de contatos : {total}")
    print(f"Enviados agora    : {enviados}")
    print(f"Pulados/enviados  : {pulados}")
    print(f"Erros             : {erros}")
    linha()

    return True


def marcar_contato_enviado(caminho_db, contato_id, erro=None):
    import sqlite3
    from datetime import datetime

    conn = sqlite3.connect(caminho_db)
    cur = conn.cursor()

    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if erro:
        cur.execute(
            """
            UPDATE contatos
            SET erro_envio = ?,
                ultima_tentativa_em = ?
            WHERE id = ?
            """,
            (str(erro)[:500], agora, contato_id)
        )
    else:
        cur.execute(
            """
            UPDATE contatos
            SET enviado = 1,
                enviado_em = ?,
                teste_enviado = 1,
                teste_enviado_em = ?,
                erro_envio = NULL,
                ultima_tentativa_em = ?
            WHERE id = ?
            """,
            (agora, agora, agora, contato_id)
        )

    conn.commit()
    conn.close()


def garantir_colunas_controle_envio(caminho_db):
    import sqlite3

    conn = sqlite3.connect(caminho_db)
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(contatos)")
    colunas = [c[1] for c in cur.fetchall()]

    campos_controle = {
        "enviado": "INTEGER DEFAULT 0",
        "enviado_em": "TEXT",
        "teste_enviado": "INTEGER DEFAULT 0",
        "teste_enviado_em": "TEXT",
        "erro_envio": "TEXT",
        "ultima_tentativa_em": "TEXT"
    }

    for campo, tipo in campos_controle.items():
        if campo not in colunas:
            cur.execute(f"ALTER TABLE contatos ADD COLUMN {campo} {tipo}")
            print(f"✅ Campo de controle criado no banco: {campo}")

    conn.commit()
    conn.close()

#!/usr/bin/env python3
import os
import sys
import re
import json
import sqlite3
import subprocess
import requests
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(__file__)
CAMP_DIR = os.path.join(BASE_DIR, "campanhas")
IMPORTAR = os.path.join(BASE_DIR, "importar_xlsx.py")
ENVIAR = os.path.join(BASE_DIR, "enviar.py")
SETUP_CRON = os.path.join(BASE_DIR, "setup_cron.sh")

load_dotenv(os.path.join(BASE_DIR, ".env"))

EVOLUTION_URL = os.getenv("EVOLUTION_URL", "").rstrip("/")
API_KEY = os.getenv("API_KEY", "")
INSTANCIA = os.getenv("INSTANCIA", "")
COLUNA_CELULAR = os.getenv("COLUNA_CELULAR", "celular")
INTERVALO = os.getenv("INTERVALO", "2")

def linha(char="─", n=60):
    print(char * n)

def listar_campanhas():
    os.makedirs(CAMP_DIR, exist_ok=True)
    return sorted([
        d for d in os.listdir(CAMP_DIR)
        if os.path.isdir(os.path.join(CAMP_DIR, d))
    ])

def status_campanha(nome):
    base = os.path.join(CAMP_DIR, nome)
    tem_xlsx = os.path.isfile(os.path.join(base, "contatos.xlsx"))
    tem_db = os.path.isfile(os.path.join(base, "contatos.db"))
    tem_msg = os.path.isfile(os.path.join(base, "mensagem.txt"))

    return " ".join([
        "📄" if tem_xlsx else "⬜",
        "🗄️" if tem_db else "⬜",
        "✉️" if tem_msg else "⬜",
    ]), tem_xlsx, tem_db, tem_msg

def normalizar_nome_planilha(nome):
    base = os.path.join(CAMP_DIR, nome)
    destino = os.path.join(base, "contatos.xlsx")

    if os.path.isfile(destino):
        return

    arquivos = [
        f for f in os.listdir(base)
        if f.lower().endswith(".xlsx") and not f.startswith("~$")
    ]

    if len(arquivos) == 1:
        os.rename(os.path.join(base, arquivos[0]), destino)
        print()
        print("✅ Planilha renomeada automaticamente:")
        print(f"   De  : {arquivos[0]}")
        print("   Para: contatos.xlsx")
    elif len(arquivos) > 1:
        print()
        print("❌ Existem várias planilhas na pasta.")
        print("Renomeie manualmente a correta para contatos.xlsx:")
        for f in arquivos:
            print(f"   - {f}")
        sys.exit(1)

def importar_se_necessario(nome):
    base = os.path.join(CAMP_DIR, nome)
    xlsx = os.path.join(base, "contatos.xlsx")
    db = os.path.join(base, "contatos.db")

    if not os.path.isfile(xlsx):
        print()
        print(f"❌ Planilha não encontrada: campanhas/{nome}/contatos.xlsx")
        sys.exit(1)

    precisa = False

    if not os.path.isfile(db):
        precisa = True
    elif os.path.getmtime(xlsx) > os.path.getmtime(db):
        precisa = True

    if precisa:
        print()
        print("📥 Importando XLSX para o banco...")
        linha()
        r = subprocess.run([sys.executable, IMPORTAR, nome], cwd=BASE_DIR)

        if r.returncode != 0:
            print()
            print("❌ Falha na importação.")
            sys.exit(1)
    else:
        print()
        print("✅ Banco já está atualizado.")

def obter_colunas(nome):
    db = os.path.join(CAMP_DIR, nome, "contatos.db")

    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(contatos)")
    colunas = [row[1] for row in cur.fetchall() if row[1] != "id"]
    conn.close()

    return colunas

def mostrar_variaveis(nome):
    colunas = obter_colunas(nome)

    print()
    print("Variáveis disponíveis nesta campanha:")
    print()

    for c in colunas:
        print(f"   {{{c}}}")

def pedir_mensagem_se_nao_existir(nome):
    msg_path = os.path.join(CAMP_DIR, nome, "mensagem.txt")

    if os.path.isfile(msg_path):
        return

    colunas = obter_colunas(nome)

    print()
    print("✉️ Nenhuma mensagem encontrada para esta campanha.")
    print()
    print("Variáveis disponíveis:")
    print()

    for c in colunas:
        print(f"   {{{c}}}")

    print()
    print("Digite a mensagem abaixo.")
    print("Use as variáveis exatamente como aparecem acima.")
    print("Quando terminar, digite uma linha contendo apenas: FIM")
    print()

    linhas = []

    while True:
        l = input()
        if l.strip().upper() == "FIM":
            break
        linhas.append(l)

    mensagem = "\n".join(linhas).strip()

    if not mensagem:
        print()
        print("❌ Mensagem vazia. Operação cancelada.")
        sys.exit(1)

    with open(msg_path, "w", encoding="utf-8") as f:
        f.write(mensagem + "\n")

    print()
    print("✅ mensagem.txt criado com sucesso.")
    print(f"Arquivo: campanhas/{nome}/mensagem.txt")

def testar_mensagem_com_primeiro_contato(nome):
    base = os.path.join(CAMP_DIR, nome)
    db_path = os.path.join(base, "contatos.db")
    msg_path = os.path.join(base, "mensagem.txt")

    if not os.path.isfile(db_path):
        print("❌ Banco não encontrado para teste.")
        return False

    if not os.path.isfile(msg_path):
        print("❌ mensagem.txt não encontrado para teste.")
        return False

    with open(msg_path, "r", encoding="utf-8") as f:
        template = f.read()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM contatos WHERE COALESCE(enviado, 0) = 0 ORDER BY id LIMIT 1")
    contato = cur.fetchone()
    conn.close()

    if not contato:
        print("❌ Nenhum contato encontrado no banco.")
        return False

    dados = dict(contato)

    try:
        mensagem = template.format_map(dados)
    except KeyError as e:
        print()
        print(f"❌ Variável não encontrada na planilha: {e}")
        print("Corrija o mensagem.txt usando apenas as variáveis listadas.")
        return False

    variaveis_pendentes = re.findall(r"{[^{}]+}", mensagem)

    print()
    print("🧪 Teste de mensagem com o primeiro contato ainda não enviado")
    linha()

    print("Contato usado no teste, ainda não enviado:")

    for k, v in dados.items():
        if k != "id":
            print(f"   {k}: {v}")

    print()
    print("Mensagem renderizada:")
    linha()
    print(mensagem)
    linha()

    if variaveis_pendentes:
        print()
        print("❌ Ainda existem variáveis não substituídas na mensagem:")
        for v in variaveis_pendentes:
            print(f"   {v}")
        print()
        print("Corrija o arquivo mensagem.txt antes de enviar.")
        return False

    numero = str(dados.get(COLUNA_CELULAR, "")).strip()

    if not numero:
        print()
        print(f"❌ Número não encontrado na coluna configurada: {COLUNA_CELULAR}")
        return False

    print()
    print("✅ Todas as variáveis foram substituídas corretamente.")

    if EVOLUTION_URL and API_KEY and INSTANCIA:
        payload = {
            "number": numero,
            "text": mensagem
        }

        print()
        print("Curl de teste gerado:")
        linha()
        print(f'curl -X POST "{EVOLUTION_URL}/message/sendText/{INSTANCIA}" \\')
        print(f'-H "apikey: {API_KEY}" \\')
        print('-H "Content-Type: application/json" \\')
        print("-d '" + json.dumps(payload, ensure_ascii=False) + "'")

        linha()
        print()
        confirmar_teste = input("Deseja enviar esta mensagem de TESTE agora? [s/N]: ").strip().lower()
        if confirmar_teste not in ["s", "sim"]:
            print("⏸️ Teste cancelado. Nenhuma mensagem foi enviada.")
            return False

        print()
        print("🚀 Enviando mensagem TESTE pela Evolution...")
        linha()
        # ZAPFLOW_TESTE_REAL_EVOLUTION
        sucesso_teste = False
        erro_teste = ""

        try:
            import urllib.request
            import urllib.error

            url_teste = f"{EVOLUTION_URL}/message/sendText/{INSTANCIA}"
            body_teste = json.dumps(payload, ensure_ascii=False).encode("utf-8")

            req = urllib.request.Request(
                url_teste,
                data=body_teste,
                headers={
                    "apikey": API_KEY,
                    "Content-Type": "application/json"
                },
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=30) as resp:
                status_code = resp.getcode()
                resposta_api = resp.read().decode("utf-8", errors="replace")

            print(f"Status HTTP: {status_code}")
            print("Resposta da API:")
            print(resposta_api)

            if 200 <= status_code < 300:
                sucesso_teste = True
            else:
                erro_teste = resposta_api

        except urllib.error.HTTPError as e:
            status_code = e.code
            erro_teste = e.read().decode("utf-8", errors="replace")
            print(f"Status HTTP: {status_code}")
            print("Resposta da API:")
            print(erro_teste)

        except Exception as e:
            erro_teste = str(e)
            print("Erro ao chamar API Evolution:")
            print(erro_teste)

        print()
        linha()

        if sucesso_teste:
            marcar_contato_enviado(os.path.join(CAMP_DIR, nome, "contatos.db"), dados.get("id"))
            print("✅ Mensagem teste enviada com sucesso.")
            print(f"✅ Contato de teste marcado como enviado: {dados.get('nome', '')} {dados.get('sobrenome', '')}".strip())
            resposta = input("Deseja continuar e enviar para toda a campanha? [s/N]: ").strip().lower()
            if resposta not in ["s", "sim"]:
                print("⏸️ Campanha não executada.")
                return False
        else:
            print("❌ Mensagem teste deu erro.")
            print(f"Erro: {erro_teste}")
            resposta = input("Deseja continuar mesmo assim? [s/N]: ").strip().lower()
            if resposta not in ["s", "sim"]:
                print("⏸️ Campanha interrompida.")
                return False

        print("🚀 Continuando para envio da campanha completa, ignorando contatos já enviados...")

        caminho_db_envio = os.path.join(CAMP_DIR, nome, "contatos.db")
        caminho_msg_envio = os.path.join(CAMP_DIR, nome, "mensagem.txt")

        with open(caminho_msg_envio, "r", encoding="utf-8") as f:
            texto_base_envio = f.read()

        enviar_campanha_completa(caminho_db_envio, texto_base_envio)
        return False
        enviar_campanha_completa(os.path.join(CAMP_DIR, nome, "contatos.db"), texto_mensagem)
        return False

        linha()

    return True

def checar_evolution():
    print()
    print("🔎 Verificando Evolution API...")
    linha()
    print(f"URL configurada      : {EVOLUTION_URL or 'NÃO CONFIGURADA'}")
    print(f"Instância configurada: {INSTANCIA or 'NÃO CONFIGURADA'}")
    print(f"API Key              : {'CARREGADA' if API_KEY else 'NÃO CONFIGURADA'}")

    if not EVOLUTION_URL or not API_KEY or not INSTANCIA:
        return False

    headers = {
        "apikey": API_KEY,
        "Content-Type": "application/json"
    }

    endpoints = [
        f"{EVOLUTION_URL}/instance/connectionState/{INSTANCIA}",
        f"{EVOLUTION_URL}/instance/fetchInstances",
    ]

    for url in endpoints:
        try:
            r = requests.get(url, headers=headers, timeout=10)

            if r.status_code in (200, 201):
                print()
                print("✅ Evolution API respondeu.")
                print(f"Status HTTP: {r.status_code}")
                print(r.text[:500])
                return True
            else:
                print()
                print(f"⚠️ Erro HTTP {r.status_code}")
                print(r.text[:300])

        except Exception as e:
            print()
            print(f"⚠️ Falha ao testar: {url}")
            print(e)

    return False

def enviar_agora(nome):
    if not testar_mensagem_com_primeiro_contato(nome):
        print()
        print("❌ Envio cancelado por falha no teste da mensagem.")
        sys.exit(1)

    confirma = input("\nConfirmar envio da campanha agora? (s/N): ").strip().lower()

    if confirma != "s":
        print("Envio cancelado.")
        return

    if not checar_evolution():
        print()
        print("❌ Envio cancelado. Evolution API não validada.")
        sys.exit(1)

    print()
    print("🚀 Iniciando envio agora...")
    linha()
    subprocess.run([sys.executable, ENVIAR, nome], cwd=BASE_DIR)

def configurar_cron(nome):
    print()
    print("⏰ Configurar envio automático via cron")
    linha()

    hora = input("Hora do envio? Ex: 10: ").strip() or "10"
    minuto = input("Minuto do envio? Ex: 00: ").strip() or "00"

    subprocess.run(["bash", SETUP_CRON, nome, hora, minuto], cwd=BASE_DIR)

def main():
    print()
    linha("═")
    print("🟢 ZapFlow — Rodar Campanha")
    linha("═")

    campanhas = listar_campanhas()

    if not campanhas:
        print()
        print("⚠️ Nenhuma campanha criada até o momento.")
        print()
        print("Crie a primeira com:")
        print("   python3 criar_campanha.py")
        print()
        sys.exit(0)

    print()
    print("Campanhas encontradas:")
    print()
    print("   📄=planilha  🗄️=banco  ✉️=mensagem")
    print()

    for i, nome in enumerate(campanhas, 1):
        icones, _, _, _ = status_campanha(nome)
        print(f"   [{i}] {nome:<30} {icones}")

    print()
    linha()

    escolha = input("Qual campanha usar? Número: ").strip()

    try:
        idx = int(escolha) - 1
    except ValueError:
        print("❌ Opção inválida.")
        sys.exit(1)

    if idx < 0 or idx >= len(campanhas):
        print("❌ Opção inválida.")
        sys.exit(1)

    nome = campanhas[idx]

    normalizar_nome_planilha(nome)
    importar_se_necessario(nome)
    mostrar_variaveis(nome)
    pedir_mensagem_se_nao_existir(nome)

    print()
    print("O que deseja fazer?")
    print()
    print("   [1] Testar mensagem com primeiro contato")
    print("   [2] Enviar campanha agora")
    print("   [3] Configurar envio automático no cron")
    print("   [4] Apenas importar/atualizar banco")
    print("   [5] Sair")
    print()

    acao = input("Escolha uma opção: ").strip()

    if acao == "1":
        testar_mensagem_com_primeiro_contato(nome)
    elif acao == "2":
        enviar_agora(nome)
    elif acao == "3":
        configurar_cron(nome)
    elif acao == "4":
        print()
        print("✅ Banco atualizado. Nenhuma mensagem enviada.")
    else:
        print()
        print("Saindo.")

if __name__ == "__main__":
    main()
