#!/usr/bin/env python3
import os
import sys

BASE_DIR = os.path.dirname(__file__)
CAMP_DIR = os.path.join(BASE_DIR, "campanhas")

def linha(char="─", n=60):
    print(char * n)

def main():
    print()
    linha("═")
    print("🟢 ZapFlow — Criar Nova Campanha")
    linha("═")
    print()

    os.makedirs(CAMP_DIR, exist_ok=True)

    nome = input("Nome da campanha: ").strip().lower().replace(" ", "_")

    if not nome:
        print("❌ Nome inválido.")
        sys.exit(1)

    camp_path = os.path.join(CAMP_DIR, nome)

    if os.path.isdir(camp_path):
        print()
        print(f"⚠️ A campanha '{nome}' já existe.")
        print(f"Pasta: {camp_path}")
        sys.exit(0)

    os.makedirs(camp_path, exist_ok=True)

    print()
    print("✅ Campanha criada com sucesso.")
    print()
    print("Agora coloque sua planilha XLSX dentro da pasta:")
    print()
    print(f"   campanhas/{nome}/")
    print()
    print("Depois execute:")
    print()
    print("   python3 rodar_campanha.py")
    print()

if __name__ == "__main__":
    main()
