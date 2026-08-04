#!/bin/bash
# =============================================================================
# BRVM Deploy - Quick Deploy Script
# =============================================================================
# Usage: ./deploy.sh [command]
#
# Commands:
#   start     - Start all services
#   stop      - Stop all services
#   restart   - Restart all services
#   status    - Show service status
#   logs      - Show service logs
#   update    - Update and rebuild services
# =============================================================================

set -e

NAS_IP="${NAS_IP:-192.168.1.64}"
NAS_SSH_PORT="${NAS_SSH_PORT:-2202}"
NAS_USER="${NAS_USER:-dkonan}"
NAS_PASS="Yaki@1606"
PROJECT_DIR="/volume1/docker/brvm"

ssh_cmd() {
    ssh -i ~/.ssh/id_ed25519 -p "$NAS_SSH_PORT" -o StrictHostKeyChecking=no "$NAS_USER@$NAS_IP" "$@"
}

ssh_sudo() {
    ssh_cmd "echo '$NAS_PASS' | sudo -S $1"
}

case "${1:-status}" in
    start)
        echo "Starting BRVM services..."
        ssh_cmd "cd $PROJECT_DIR && docker compose up -d"
        ;;
    stop)
        echo "Stopping BRVM services..."
        ssh_cmd "cd $PROJECT_DIR && docker compose down"
        ;;
    restart)
        echo "Restarting BRVM services..."
        ssh_cmd "cd $PROJECT_DIR && docker compose restart"
        ;;
    status)
        echo "BRVM Service Status:"
        ssh_cmd "cd $PROJECT_DIR && docker compose ps"
        ;;
    logs)
        ssh_cmd "cd $PROJECT_DIR && docker compose logs -f --tail=50"
        ;;
    update)
        echo "Updating BRVM services..."
        ssh_cmd "cd $PROJECT_DIR && docker compose down"
        ssh_cmd "cd $PROJECT_DIR && docker compose build --no-cache"
        ssh_cmd "cd $PROJECT_DIR && docker compose up -d"
        echo "Update complete!"
        ;;
    *)
        echo "Usage: ./deploy.sh [start|stop|restart|status|logs|update]"
        exit 1
        ;;
esac
