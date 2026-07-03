#!/bin/bash
set -e

BASE="/opt/fortigate-monitor"
SERVICE="/etc/systemd/system/fortigate-monitor.service"

echo "Instalando FortiGate Monitor..."

dnf install -y python39 python39-pip sqlite rsyslog git

cd "$BASE"

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt

if [ ! -f "$BASE/config.yaml" ]; then
    cp "$BASE/config.yaml.example" "$BASE/config.yaml"
    echo "Se creó config.yaml desde el ejemplo. Debes editarlo."
fi

python3 -m py_compile collector.py
python3 -m py_compile modules/*.py

cat > "$SERVICE" << EOF
[Unit]
Description=FortiGate Monitor Collector
After=network.target rsyslog.service

[Service]
Type=simple
WorkingDirectory=$BASE
ExecStart=$BASE/venv/bin/python3 $BASE/collector.py
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable fortigate-monitor

echo "Instalación completada."
echo "Editar configuración:"
echo "vi $BASE/config.yaml"
echo ""
echo "Iniciar servicio:"
echo "systemctl start fortigate-monitor"
echo ""
echo "Ver estado:"
echo "systemctl status fortigate-monitor"
