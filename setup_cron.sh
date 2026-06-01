#!/bin/bash
# ZapFlow — setup_cron.sh
# Agenda o envio de uma campanha via crontab
#
# Uso:
#   bash setup_cron.sh <nome_da_campanha> <hora> <minuto>
#
# Exemplo (rodar às 10h00):
#   bash setup_cron.sh minha_campanha 10 00

CAMPANHA=${1:-""}
HORA=${2:-10}
MINUTO=${3:-00}

if [ -z "$CAMPANHA" ]; then
    echo "Uso: bash setup_cron.sh <nome_da_campanha> <hora> <minuto>"
    echo "Exemplo: bash setup_cron.sh evento_maio 10 00"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$SCRIPT_DIR/enviar.py"
LOG="$SCRIPT_DIR/campanhas/$CAMPANHA/envio.log"

CRON_LINE="$MINUTO $HORA * * * cd $SCRIPT_DIR && python3 $SCRIPT $CAMPANHA >> $LOG 2>&1"

# Remove entrada antiga para essa campanha, adiciona nova
( crontab -l 2>/dev/null | grep -v "enviar.py $CAMPANHA" ; echo "$CRON_LINE" ) | crontab -

echo ""
echo "✅ Cron configurado!"
echo "   Campanha  : $CAMPANHA"
echo "   Horário   : ${HORA}h${MINUTO}"
echo "   Script    : $SCRIPT"
echo "   Log       : $LOG"
echo ""
echo "Para confirmar : crontab -l"
echo "Para rodar agora: python3 $SCRIPT $CAMPANHA"
