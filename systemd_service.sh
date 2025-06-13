# File: /etc/systemd/system/jagapadi.service
[Unit]
Description=JAGAPADI v2.0 Flask Web Server
After=network.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/jagapadi
Environment=PATH=/home/pi/jagapadi/venv/bin
ExecStart=/home/pi/jagapadi/venv/bin/python flask_server.py
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=jagapadi

[Install]
WantedBy=multi-user.target

# Untuk menginstall service:
# sudo cp jagapadi.service /etc/systemd/system/
# sudo systemctl daemon-reload
# sudo systemctl enable jagapadi
# sudo systemctl start jagapadi

# Untuk melihat status:
# sudo systemctl status jagapadi

# Untuk melihat log:
# sudo journalctl -u jagapadi -f