#!/bin/bash
set -eu

TERMINAL_WIDTH=$(tput cols 2>/dev/null || echo 80)
SEPARATOR=$(printf '=%.0s' $(seq 1 $TERMINAL_WIDTH))

PACKAGE_NAME="python_template_server"
WD=$(pwd)
LOG_FILE="python-template-server.log"
SERVICE_FILE="python-template-server.service"
START_SERVICE_FILE="start_service.sh"
STOP_SERVICE_FILE="stop_service.sh"
UNINSTALL_FILE="uninstall_template_server.sh"

LOG_PATH="${WD}/${LOG_FILE}"
SERVICE_PATH="${WD}/${SERVICE_FILE}"
START_SERVICE_PATH="${WD}/${START_SERVICE_FILE}"
STOP_SERVICE_PATH="${WD}/${STOP_SERVICE_FILE}"
UNINSTALL_PATH="${WD}/${UNINSTALL_FILE}"

echo ${SEPARATOR}
if [ -t 0 ]; then
    read -p "Enter the port number (default 443): " port
    port=${port:-443}
    echo
    echo "Enter the API token hash (leave blank to auto-generate on first run):"
    read -p "API_TOKEN_HASH: " api_token_hash
else
    echo "No terminal detected. Using default port 443 and auto-generating token."
    port=443
    api_token_hash=""
fi

echo "Creating service..."
cat > "${SERVICE_PATH}" << EOF
[Unit]
Description=Python Template Server
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${WD}
User=${USER}
Environment=PORT=${port}
Environment=API_TOKEN_HASH=${api_token_hash}
ExecStart=docker compose up -d
ExecStop=docker compose down
Restart=on-failure
RestartSec=5s
StandardOutput=append:${LOG_PATH}
StandardError=append:${LOG_PATH}

ProtectSystem=full
ReadWriteDirectories=${WD}

[Install]
WantedBy=multi-user.target
EOF

echo "Creating service creation script..."
cat > "${START_SERVICE_PATH}" << EOF
#!/bin/bash
set -eu

if systemctl is-active --quiet ${SERVICE_FILE}; then
    echo "Service is already running. Stopping..."
    sudo systemctl stop ${SERVICE_FILE}
fi

if systemctl is-enabled --quiet ${SERVICE_FILE}; then
    echo "Service is already enabled. Disabling..."
    sudo systemctl disable ${SERVICE_FILE}
fi

if [ -f /etc/systemd/system/${SERVICE_FILE} ]; then
    echo "Removing existing service file..."
    sudo rm -f /etc/systemd/system/${SERVICE_FILE}
fi

echo "Creating service..."
sudo cp ${SERVICE_PATH} /etc/systemd/system
sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_FILE}

echo "Starting service..."
sudo systemctl start ${SERVICE_FILE}
sudo systemctl status ${SERVICE_FILE}
EOF
chmod +x "${START_SERVICE_PATH}"

echo "Creating service stop script..."
cat > "${STOP_SERVICE_PATH}" << EOF
#!/bin/bash
set -eu

echo "Stopping service..."
sudo systemctl stop ${SERVICE_FILE}

read -p "Disable service? (y/n): " disable_service
if [ "\$disable_service" == "y" ]; then
    echo "Disabling service..."
    sudo systemctl disable ${SERVICE_FILE}
    sudo systemctl daemon-reload
    sudo rm -f /etc/systemd/system/${SERVICE_FILE}
fi

EOF
chmod +x "${STOP_SERVICE_PATH}"

echo "Creating uninstall script..."
cat > "${UNINSTALL_PATH}" << EOF
#!/bin/bash
set -eu

if systemctl is-active --quiet ${SERVICE_FILE}; then
    echo "Service is running. Stopping..."
    sudo systemctl stop ${SERVICE_FILE}
fi

if [ -f /etc/systemd/system/${SERVICE_FILE} ]; then
    echo "Service is enabled. Disabling..."
    sudo systemctl disable ${SERVICE_FILE}
    sudo systemctl daemon-reload
    sudo rm -f /etc/systemd/system/${SERVICE_FILE}
fi

rm -rf *
EOF
chmod +x "${UNINSTALL_PATH}"

echo "${SEPARATOR}"
echo "Python Template Server has been installed successfully."
echo
echo "To create a start-up service for the Python Template Server, run: './${START_SERVICE_FILE}'"
echo "To stop the service, run: './${STOP_SERVICE_FILE}'"
echo "To change the port or API token, edit the service file and then run the start service script: ${SERVICE_PATH}"
echo "To view the logs: 'cat ${LOG_FILE}'"
echo "To uninstall, run: './${UNINSTALL_FILE}'"
echo
echo "Note: You may need to add your user to the Docker group and log out/in for permission changes to take effect."
echo "      Command: sudo usermod -aG docker \${USER}"
echo "${SEPARATOR}"

rm -- "$0"
