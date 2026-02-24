#!/bin/bash
# Shadow Nexus C2 Server - Automated Installation
# For Ubuntu/Debian systems

set -e

echo "=========================================="
echo "Shadow Nexus C2 Server Installation"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Python3 is installed
echo -e "${GREEN}[1/7] Checking Python3 installation...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python3 is not installed${NC}"
    echo "Please install Python3 first:"
    echo "  apt update && apt install -y python3 python3-pip python3-venv"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}Found: $PYTHON_VERSION${NC}"
apt update
apt install -y python3 python3-pip python3-venv

# Check if pip is installed
echo -e "${GREEN}[2/7] Checking pip installation...${NC}"
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}Error: pip3 is not installed${NC}"
    echo "Please install pip3 first:"
    echo "  apt install -y python3-pip"
    exit 1
fi

PIP_VERSION=$(pip3 --version)
echo -e "${GREEN}Found: $PIP_VERSION${NC}"

# Navigate to server directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SERVER_DIR="$SCRIPT_DIR/server"

if [ ! -d "$SERVER_DIR" ]; then
    echo -e "${RED}Error: server directory not found at $SERVER_DIR${NC}"
    exit 1
fi

cd "$SERVER_DIR"

# Create virtual environment
echo -e "${GREEN}[3/7] Creating Python virtual environment...${NC}"
if [ ! -d "venv" ]; then
    if python3 -m venv venv 2>/dev/null; then
        echo -e "${GREEN}Virtual environment created${NC}"
    else
        echo -e "${RED}Error: Failed to create virtual environment${NC}"
        echo -e "${YELLOW}This usually means python3-venv is not installed${NC}"
        echo ""
        echo "Please install it with:"
        PYTHON_MINOR=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
        echo -e "${YELLOW}  apt install python${PYTHON_MINOR}-venv${NC}"
        echo "OR"
        echo -e "${YELLOW}  apt install python3-venv${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}Virtual environment already exists${NC}"
fi

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies with EXACT versions
echo -e "${GREEN}[4/7] Installing Python dependencies (exact versions)...${NC}"
pip3 install --upgrade pip
pip3 install -r requirements.txt

# Verify config.json exists
echo -e "${GREEN}[5/7] Checking configuration files...${NC}"
if [ ! -f "config.json" ]; then
    echo -e "${YELLOW}Warning: config.json not found${NC}"
    echo -e "${YELLOW}Creating template config.json...${NC}"
    cat > config.json << 'EOF'
{
  "crowdstrike": {
    "client_id": "YOUR_CLIENT_ID_HERE",
    "client_secret": "YOUR_CLIENT_SECRET_HERE"
  },
  "execution": {
    "default_timeout": 300,
    "default_poll_interval": 5
  }
}
EOF
    echo -e "${RED}IMPORTANT: Edit config.json with your CrowdStrike credentials!${NC}"
else
    echo -e "${GREEN}config.json found${NC}"
fi

# Check other required config files
echo ""
echo "Checking additional configuration files:"
for file in prompts.json victims.json fallback_payloads.json; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}  ✗ $file not found${NC}"
    else
        echo -e "${GREEN}  ✓ $file found${NC}"
    fi
done

# Create launcher script
echo ""
echo -e "${GREEN}[6/7] Creating server launcher script...${NC}"
cat > start-c2-server.sh << 'LAUNCHER_EOF'
#!/bin/bash
# Shadow Nexus C2 Server Launcher

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${CYAN}=========================================="
echo "Shadow Nexus C2 Server"
echo -e "==========================================${NC}"
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo -e "${RED}Error: Virtual environment not found!${NC}"
    echo "Please run setup-c2-server.sh first"
    exit 1
fi

# Check if config.json has credentials
if grep -q "YOUR_CLIENT_ID_HERE" config.json 2>/dev/null; then
    echo -e "${YELLOW}⚠ Warning: CrowdStrike credentials not configured!${NC}"
    echo -e "${YELLOW}Edit config.json before starting the server${NC}"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Exiting. Please configure credentials first."
        exit 1
    fi
fi

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment...${NC}"
source venv/bin/activate

# Check if app.py exists
if [ ! -f "app.py" ]; then
    echo -e "${RED}Error: app.py not found!${NC}"
    exit 1
fi

# Get local IP for display
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}')

# Start server
echo -e "${GREEN}Starting C2 Server...${NC}"
echo ""
echo -e "${CYAN}Server will be available at:${NC}"
echo -e "  ${GREEN}http://0.0.0.0:5000${NC} (all interfaces)"
echo -e "  ${GREEN}http://localhost:5000${NC} (local)"
if [ ! -z "$LOCAL_IP" ]; then
    echo -e "  ${GREEN}http://${LOCAL_IP}:5000${NC} (network)"
fi
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo -e "${CYAN}==========================================${NC}"
echo ""

# Run the server
python3 app.py
LAUNCHER_EOF

chmod +x start-c2-server.sh
echo -e "${GREEN}Launcher script created: start-c2-server.sh${NC}"

# Verify environment
echo ""
echo -e "${GREEN}[7/7] Verifying environment...${NC}"
if [ -f "verify_environment.py" ]; then
    python3 verify_environment.py
else
    echo -e "${YELLOW}verify_environment.py not found, skipping verification${NC}"
fi

# Deactivate venv for clean exit
deactivate

echo ""
echo -e "${GREEN}=========================================="
echo "Installation Complete!"
echo "==========================================${NC}"
echo ""
echo -e "${CYAN}✓ Python virtual environment created${NC}"
echo -e "${CYAN}✓ Dependencies installed${NC}"
echo -e "${CYAN}✓ Server launcher created${NC}"
echo ""
echo -e "${GREEN}To start the C2 server:${NC}"
echo -e "${YELLOW}  cd $SERVER_DIR${NC}"
echo -e "${YELLOW}  ./start-c2-server.sh${NC}"
echo ""
echo "Server will run on: http://0.0.0.0:5000"
echo ""

# Check if credentials need configuration
if grep -q "YOUR_CLIENT_ID_HERE" config.json 2>/dev/null; then
    echo -e "${RED}⚠ IMPORTANT: Configure CrowdStrike credentials before starting!${NC}"
    echo ""
    echo "Edit credentials with:"
    echo "  nano $SERVER_DIR/config.json"
    echo ""
fi

echo -e "${GREEN}Installation completed successfully!${NC}"
