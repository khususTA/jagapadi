#!/bin/bash

# setup.sh - Script instalasi JAGAPADI v2.0 untuk Raspberry Pi
# Jalankan dengan: bash setup.sh

set -e  # Exit on any error

echo "🌾 ============================================="
echo "   JAGAPADI v2.0 Setup untuk Raspberry Pi"
echo "============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[ℹ]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Check if running on Raspberry Pi
print_info "Checking system..."
if ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    print_warning "Tidak terdeteksi sebagai Raspberry Pi, melanjutkan setup..."
fi

# Set installation directory
INSTALL_DIR="/home/pi/jagapadi"
if [ "$USER" != "pi" ]; then
    INSTALL_DIR="/home/$USER/jagapadi"
    print_info "User bukan 'pi', menggunakan direktori: $INSTALL_DIR"
fi

print_info "Direktori instalasi: $INSTALL_DIR"

# Create installation directory
print_info "Membuat direktori instalasi..."
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Create folder structure
print_info "Membuat struktur folder..."
mkdir -p templates static/css static/js
mkdir -p hasil_dekripsi cache_history client_logs uploads

print_status "Struktur folder dibuat"

# Update system
print_info "Updating sistem..."
sudo apt update -qq
print_status "Sistem updated"

# Install Python and pip
print_info "Installing Python dependencies..."
sudo apt install -y python3 python3-pip python3-venv python3-dev
print_status "Python dependencies installed"

# Create virtual environment
print_info "Membuat Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_status "Virtual environment dibuat"
else
    print_warning "Virtual environment sudah ada"
fi

# Activate virtual environment
source venv/bin/activate

# Install Python packages
print_info "Installing Python packages..."
pip install --upgrade pip -q
pip install flask pycryptodome psutil -q
print_status "Python packages installed"

# Check for required files
print_info "Checking for required files..."

required_files=("aes_deskripsi.py")
missing_files=()

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        missing_files+=("$file")
    fi
done

if [ ${#missing_files[@]} -ne 0 ]; then
    print_error "File yang diperlukan tidak ditemukan:"
    for file in "${missing_files[@]}"; do
        echo "  - $file"
    done
    print_info "Silakan copy file-file tersebut ke $INSTALL_DIR"
    print_info "Kemudian jalankan script ini lagi"
    exit 1
fi

# Check for HTML/CSS/JS files
html_files=("templates/index.html" "static/css/style.css" "static/js/script.js")
html_missing=()

for file in "${html_files[@]}"; do
    if [ ! -f "$file" ]; then
        html_missing+=("$file")
    fi
done

if [ ${#html_missing[@]} -ne 0 ]; then
    print_warning "File HTML/CSS/JS tidak ditemukan:"
    for file in "${html_missing[@]}"; do
        echo "  - $file"
    done
    print_info "Silakan copy file HTML, CSS, dan JS ke lokasi yang sesuai"
fi

# Create flask_server.py if not exists
if [ ! -f "flask_server.py" ]; then
    print_info "Flask server file tidak ditemukan"
    print_info "Silakan copy flask_server.py dari artifact yang diberikan"
    print_info "Atau buat file flask_server.py dengan konten yang sesuai"
fi

# Set up configuration
print_info "Setting up configuration..."

# Ask for server IP
read -p "Masukkan IP server AI (default: 192.168.1.100): " server_ip
server_ip=${server_ip:-192.168.1.100}

# Update server IP in flask_server.py if it exists
if [ -f "flask_server.py" ]; then
    sed -i "s/SERVER_HOST = '.*'/SERVER_HOST = '$server_ip'/" flask_server.py
    print_status "Server IP updated to $server_ip"
fi

# Create startup script
print_info "Creating startup script..."
cat > start_jagapadi.sh << EOF
#!/bin/bash
cd "$INSTALL_DIR"
source venv/bin/activate
python flask_server.py
EOF

chmod +x start_jagapadi.sh
print_status "Startup script dibuat: start_jagapadi.sh"

# Create systemd service
print_info "Setting up systemd service..."
cat > jagapadi.service << EOF
[Unit]
Description=JAGAPADI v2.0 Flask Web Server
After=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/venv/bin
ExecStart=$INSTALL_DIR/venv/bin/python flask_server.py
Restart=always
RestartSec=10

StandardOutput=journal
StandardError=journal
SyslogIdentifier=jagapadi

[Install]
WantedBy=multi-user.target
EOF

# Ask if user wants to install service
read -p "Install sebagai system service? (y/n, default: n): " install_service
if [ "$install_service" = "y" ] || [ "$install_service" = "Y" ]; then
    sudo cp jagapadi.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable jagapadi
    print_status "System service installed dan enabled"
    print_info "Gunakan 'sudo systemctl start jagapadi' untuk memulai"
    print_info "Gunakan 'sudo systemctl status jagapadi' untuk melihat status"
else
    print_info "System service tidak diinstall"
    print_info "Gunakan './start_jagapadi.sh' untuk menjalankan manual"
fi

# Get local IP
LOCAL_IP=$(hostname -I | awk '{print $1}')

# Create test script
print_info "Creating test script..."
cat > test_server.sh << EOF
#!/bin/bash
echo "Testing JAGAPADI server..."
echo "Local IP: $LOCAL_IP"
echo "Testing connection to http://$LOCAL_IP:5000"
curl -s http://$LOCAL_IP:5000/api/status || echo "Server not running"
EOF

chmod +x test_server.sh

# Create info script
cat > info.sh << EOF
#!/bin/bash
echo "🌾 JAGAPADI v2.0 - System Information"
echo "=================================="
echo "Installation Directory: $INSTALL_DIR"
echo "Local IP: $LOCAL_IP"
echo "Web Interface: http://$LOCAL_IP:5000"
echo "Target AI Server: $server_ip:12345"
echo ""
echo "Files:"
echo "  - Results: $INSTALL_DIR/hasil_dekripsi"
echo "  - History: $INSTALL_DIR/cache_history" 
echo "  - Logs: $INSTALL_DIR/client_logs"
echo ""
echo "Commands:"
echo "  Start: ./start_jagapadi.sh"
echo "  Test: ./test_server.sh"
echo "  Info: ./info.sh"
if [ -f "/etc/systemd/system/jagapadi.service" ]; then
echo "  Service: sudo systemctl start jagapadi"
fi
echo ""
echo "Browser: http://$LOCAL_IP:5000"
EOF

chmod +x info.sh

print_status "Test dan info scripts dibuat"

# Final setup
print_info "Final setup..."

# Set permissions
chmod -R 755 "$INSTALL_DIR"
chown -R $USER:$USER "$INSTALL_DIR" 2>/dev/null || true

print_status "Permissions set"

# Summary
echo ""
echo "🎉 ============================================="
echo "   JAGAPADI v2.0 Setup SELESAI!"
echo "============================================="
echo ""
print_status "Installation directory: $INSTALL_DIR"
print_status "Local IP: $LOCAL_IP"
print_status "Web interface: http://$LOCAL_IP:5000"
print_status "Target AI server: $server_ip:12345"
echo ""

if [ ${#html_missing[@]} -eq 0 ] && [ -f "flask_server.py" ]; then
    print_info "✅ Semua file lengkap! Siap untuk dijalankan."
    echo ""
    print_info "Untuk memulai:"
    echo "  cd $INSTALL_DIR"
    if [ "$install_service" = "y" ] || [ "$install_service" = "Y" ]; then
        echo "  sudo systemctl start jagapadi"
    else
        echo "  ./start_jagapadi.sh"
    fi
    echo ""
    print_info "Kemudian buka browser ke: http://$LOCAL_IP:5000"
else
    print_warning "⚠️  Setup hampir selesai, namun ada file yang kurang:"
    if [ ${#html_missing[@]} -ne 0 ]; then
        echo "  HTML/CSS/JS files"
    fi
    if [ ! -f "flask_server.py" ]; then
        echo "  flask_server.py"
    fi
    echo ""
    print_info "Silakan copy file yang kurang, kemudian jalankan:"
    echo "  cd $INSTALL_DIR"
    echo "  ./start_jagapadi.sh"
fi

echo ""
echo "📋 Untuk informasi lengkap: ./info.sh"
echo "🧪 Untuk test server: ./test_server.sh"
echo ""
print_status "Setup completed!"
