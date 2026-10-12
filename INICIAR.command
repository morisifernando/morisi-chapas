#!/bin/bash
cd "$(dirname "$0")"
echo ""
echo "  ========================================"
echo "     Chapas Perforadas Cordini - Iniciando..."
echo "  ========================================"
echo ""

if ! command -v python3 &>/dev/null; then
  echo "  [ERROR] No se encontro Python 3."
  echo "  Instala Python desde https://www.python.org/downloads/"
  read -n 1 -s -r -p "  Presiona una tecla para salir..."
  exit 1
fi

if ! python3 -m pip show streamlit &>/dev/null; then
  echo "  Instalando librerias la primera vez..."
  python3 -m pip install -r requirements.txt
fi

echo "  Abriendo la app en el navegador..."
echo "  (Para cerrar: cierra esta ventana o Ctrl+C)"
echo ""
python3 -m streamlit run app.py --server.headless true --browser.gatherUsageStats false
