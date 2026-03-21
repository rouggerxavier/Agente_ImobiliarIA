# SYSTEMD.md

Este arquivo descreve como manter o backend `Agente_ImobiliarIA` rodando em produção na VM Oracle.

## 1) Arquivo do serviço

Crie o arquivo abaixo em:

`/etc/systemd/system/agente-imobiliaria.service`

```ini
[Unit]
Description=Agente Imobiliaria FastAPI
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/Agente_ImobiliarIA
EnvironmentFile=/home/ubuntu/Agente_ImobiliarIA/.env
ExecStart=/home/ubuntu/Agente_ImobiliarIA/.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8010
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

## 2) Ativar o serviço

```bash
sudo systemctl daemon-reload
sudo systemctl enable agente-imobiliaria.service
sudo systemctl start agente-imobiliaria.service
```

## 3) Verificar status e logs

```bash
sudo systemctl status agente-imobiliaria.service
journalctl -u agente-imobiliaria.service -f
```

## 4) Reiniciar após deploy

```bash
sudo systemctl restart agente-imobiliaria.service
```

## 5) Pré-requisitos de rede

- Security List/NSG Oracle: liberar TCP 8010 (ingress)
- iptables/host firewall: aceitar TCP 8010

```bash
sudo iptables -I INPUT 1 -p tcp --dport 8010 -j ACCEPT
```

Para persistir regras:

```bash
sudo apt-get install -y iptables-persistent
sudo netfilter-persistent save
```
