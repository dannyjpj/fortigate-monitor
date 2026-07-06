# Instalación

## Requisitos

- Linux Rocky/CentOS/RHEL
- Python 3.9+
- Git
- SQLite
- OpenSSL
- Acceso API al FortiGate
- Acceso SSH al FortiGate

## Instalación

```bash
git clone <REPOSITORIO>
cd fortigate-monitor
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp config.yaml.example config.yaml
