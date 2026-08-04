#!/bin/bash
# =============================================================================
# BRVM Trading Platform - Installation Script
# =============================================================================
# Usage: ./install.sh [nas_ip] [nas_ssh_port] [nas_user]
#
# Example:
#   ./install.sh 192.168.1.64 2202 dkonan
# =============================================================================

set -e

# Configuration
NAS_IP="${1:-192.168.1.64}"
NAS_SSH_PORT="${2:-2202}"
NAS_USER="${3:-dkonan}"
NAS_PASS="Yaki@1606"
PROJECT_DIR="/volume1/docker/brvm"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_banner() {
    echo -e "${BLUE}"
    echo "=================================================="
    echo "  BRVM Trading Platform - Installation"
    echo "=================================================="
    echo -e "${NC}"
}

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# SSH command wrapper
ssh_cmd() {
    ssh -i ~/.ssh/id_ed25519 -p "$NAS_SSH_PORT" -o StrictHostKeyChecking=no "$NAS_USER@$NAS_IP" "$@"
}

ssh_sudo() {
    ssh_cmd "echo '$NAS_PASS' | sudo -S $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v ssh &> /dev/null; then
        log_error "SSH not found. Please install OpenSSH."
        exit 1
    fi

    if ! command -v scp &> /dev/null; then
        log_error "SCP not found. Please install OpenSSH."
        exit 1
    fi

    if [ ! -f ~/.ssh/id_ed25519 ]; then
        log_warn "SSH key not found at ~/.ssh/id_ed25519"
        log_info "Generating SSH key..."
        ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N "" -C "brvm-deploy"
        log_info "Please add this public key to your NAS:"
        cat ~/.ssh/id_ed25519.pub
        echo ""
        read -p "Press Enter after adding the key to NAS..."
    fi

    log_info "Prerequisites OK"
}

# Test NAS connection
test_connection() {
    log_info "Testing connection to NAS ($NAS_IP:$NAS_SSH_PORT)..."

    if ! ssh_cmd "echo 'Connection OK'" 2>/dev/null; then
        log_error "Cannot connect to NAS. Check IP, port, and SSH key."
        exit 1
    fi

    log_info "NAS connection OK"
}

# Create directory structure on NAS
create_directories() {
    log_info "Creating directory structure on NAS..."

    ssh_sudo "mkdir -p $PROJECT_DIR/{db,scraper,api,grafana/{provisioning/datasources,dashboards}}"

    log_info "Directories created"
}

# Transfer files to NAS
transfer_files() {
    log_info "Transferring files to NAS..."

    # Use tar + ssh for efficient transfer
    tar czf - \
        -C "$SCRIPT_DIR" \
        docker-compose.yml \
        .env.example \
        db/init.sql \
        scraper/ \
        api/ \
        grafana/ \
        | ssh_cmd "cat | tar xzf - -C $PROJECT_DIR"

    # Create .env from .env.example if not exists
    ssh_cmd "test -f $PROJECT_DIR/.env || cp $PROJECT_DIR/.env.example $PROJECT_DIR/.env"

    log_info "Files transferred"
}

# Build Docker images
build_images() {
    log_info "Building Docker images on NAS..."

    ssh_cmd "cd $PROJECT_DIR && docker compose build --no-cache"

    log_info "Docker images built"
}

# Start services
start_services() {
    log_info "Starting BRVM services..."

    ssh_cmd "cd $PROJECT_DIR && docker compose up -d"

    log_info "Waiting for services to start..."
    sleep 10

    # Check health
    log_info "Checking service status..."
    ssh_cmd "cd $PROJECT_DIR && docker compose ps"
}

# Import historical data (optional)
import_data() {
    read -p "Do you want to import historical data from GitHub? (y/n) " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Importing historical data..."

        # Clone repo
        ssh_cmd "cd /tmp && git clone https://github.com/dkonanjp/dbbrvm.git brvm-data 2>/dev/null || true"

        # Import CSV files
        ssh_cmd "cd /tmp/brvm-data && for f in dbhistorical/*.csv; do
            ticker=\$(basename \"\$f\" .csv)
            psql -h brvm-postgres -U brvm_bot -d brvm -c \"\\COPY daily(ticker, date, open, high, low, close, volume, variation) FROM '\$f' WITH CSV HEADER;\" 2>/dev/null || true
        done"

        # Clean up
        ssh_cmd "rm -rf /tmp/brvm-data"

        log_info "Historical data imported"
    fi
}

# Setup GitHub mirror
setup_mirror() {
    read -p "Do you want to setup GitLab mirror? (y/n) " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Setting up GitLab mirror..."

        # Enable GitLab mirroring via API
        ssh_cmd "curl -s -X POST 'http://localhost:8088/api/v4/projects/root%2Fbrvm-data/mirror/pull' \
            -H 'PRIVATE-TOKEN: glpat-BEeoxnihJPizTAULoQ02VG86MQp1OjEH.01.0w1b5pe85' > /dev/null"

        log_info "GitLab mirror configured"
    fi
}

# Print summary
print_summary() {
    echo ""
    echo -e "${GREEN}=================================================="
    echo "  Installation Complete!"
    echo "==================================================${NC}"
    echo ""
    echo "Services:"
    echo "  - PostgreSQL:  $NAS_IP:5433"
    echo "  - Grafana:     http://$NAS_IP:3000"
    echo "  - API:         http://$NAS_IP:8000"
    echo "  - GitLab:      http://$NAS_IP:8088"
    echo ""
    echo "Credentials:"
    echo "  - PostgreSQL:  brvm_bot / BrvmSecure2026!"
    echo "  - Grafana:     admin / admin123"
    echo "  - GitLab:      root / (see README)"
    echo ""
    echo "Dashboard:"
    echo "  http://$NAS_IP:3000/d/brvm-main-dashboard/brvm-tableau-de-bord-boursier"
    echo ""
    echo "API Docs:"
    echo "  http://$NAS_IP:8000/docs"
    echo ""
}

# Main
main() {
    print_banner

    check_prerequisites
    test_connection
    create_directories
    transfer_files
    build_images
    start_services
    import_data
    setup_mirror
    print_summary
}

main
