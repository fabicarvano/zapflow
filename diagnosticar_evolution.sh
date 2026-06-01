#!/bin/bash

source .env

echo "=== 1. Testando se a Evolution responde ==="
curl -i -s "$EVOLUTION_URL" | head -30

echo
echo "=== 2. Testando rota padrão de instâncias com API_KEY atual ==="
curl -i -s -X GET "$EVOLUTION_URL/instance/fetchInstances" \
-H "apikey: $API_KEY"

echo
echo
echo "=== 3. Testando estado da instância configurada ==="
curl -i -s -X GET "$EVOLUTION_URL/instance/connectionState/$INSTANCIA" \
-H "apikey: $API_KEY"

echo
echo
echo "=== 4. Testando documentação/API docs se existir ==="
curl -i -s "$EVOLUTION_URL/docs" | head -30

echo
echo "=== 5. Verificando container/serviço local, se existir Docker ==="
docker ps 2>/dev/null | grep -i evolution || echo "Nenhum container Evolution encontrado no Docker local, ou Docker indisponível."

echo
echo "=== Diagnóstico concluído ==="
