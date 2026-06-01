import os
import json
import urllib.request
import urllib.error
from pathlib import Path

ENV_FILE = Path(".env")
EVOLUTION_URL = "http://207.38.88.213:8080"
ADMIN_API_KEY = "35d70b8dfd8345429323a124ca38639eb17d9883bbfaf5ac3813bbe397c47893"

def linha():
    print("─" * 60)

def request(method, path, payload=None, apikey=ADMIN_API_KEY):
    url = f"{EVOLUTION_URL}{path}"
    data = None

    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "apikey": apikey,
            "Content-Type": "application/json"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.getcode(), body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return e.code, body
    except Exception as e:
        return 0, str(e)

def atualizar_env(instancia, token):
    txt = ENV_FILE.read_text(encoding="utf-8")

    txt = txt.replace(
        next((l for l in txt.splitlines() if l.startswith("API_KEY=")), "API_KEY="),
        f"API_KEY={token}"
    )

    txt = txt.replace(
        next((l for l in txt.splitlines() if l.startswith("INSTANCIA=")), "INSTANCIA="),
        f"INSTANCIA={instancia}"
    )

    ENV_FILE.write_text(txt, encoding="utf-8")

print()
print("🟢 Criar nova instância Evolution")
linha()

nome = input("Nome da nova instância: ").strip()
numero = input("Número do WhatsApp com DDI/DDD, ex: 5521999999999: ").strip()

if not nome or not numero:
    print("❌ Nome da instância e número são obrigatórios.")
    raise SystemExit(1)

print()
print("=== 1. Criando instância ===")
linha()

payload_criar = {
    "instanceName": nome,
    "integration": "WHATSAPP-BAILEYS",
    "qrcode": True,
    "pairingCode": True,
    "number": numero
}

status, body = request("POST", "/instance/create", payload_criar)

print(f"Status HTTP: {status}")
print(body)

if status not in [200, 201]:
    print("❌ Erro ao criar instância.")
    raise SystemExit(1)

try:
    data = json.loads(body)
except:
    data = {}

token = (
    data.get("hash")
    or data.get("token")
    or data.get("instance", {}).get("token")
    or data.get("instance", {}).get("apikey")
)

print()
print("=== 2. Solicitando código de pareamento ===")
linha()

status2, body2 = request("GET", f"/instance/connect/{nome}?number={numero}")

print(f"Status HTTP: {status2}")
print(body2)

pairing_code = ""

try:
    data2 = json.loads(body2)
    pairing_code = (
        data2.get("pairingCode")
        or data2.get("code")
        or data2.get("base64")
        or data2.get("qrcode", {}).get("pairingCode")
        or data2.get("qrcode", {}).get("code")
    )
except:
    pass

print()
linha()

if pairing_code:
    print("✅ Código de pareamento recebido:")
    print()
    print(pairing_code)
else:
    print("⚠️ A API não retornou pairingCode explícito.")
    print("Veja a resposta acima. Pode ter retornado QR Code/base64 em vez de código.")

if token:
    print()
    print("✅ Token da instância encontrado.")
    atualizar = input("Deseja atualizar o .env com essa instância/token? [s/N]: ").strip().lower()

    if atualizar in ["s", "sim"]:
        atualizar_env(nome, token)
        print("✅ .env atualizado com sucesso.")
else:
    print()
    print("⚠️ Token da instância não identificado automaticamente.")
    print("Liste as instâncias para pegar o token manualmente:")
    print(f'curl -s -X GET "{EVOLUTION_URL}/instance/fetchInstances" -H "apikey: {ADMIN_API_KEY}"')

print()
print("=== 3. Conferindo estado da instância ===")
linha()

status3, body3 = request("GET", f"/instance/connectionState/{nome}")
print(f"Status HTTP: {status3}")
print(body3)

print()
print("✅ Script finalizado.")
