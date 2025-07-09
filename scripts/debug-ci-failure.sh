#!/bin/bash
# Debug script for CI failures
# This script helps diagnose intermittent CI failures by collecting detailed information

set -e

echo "=== CI Debug Information ==="
echo "Date: $(date)"
echo "Environment: $CI"
echo

echo "=== System Information ==="
uname -a
echo "CPU cores: $(nproc)"
echo "Memory: $(free -h | grep Mem | awk '{print $2}')"
echo "Disk space:"
df -h
echo

echo "=== Docker Information ==="
docker --version
docker-compose --version
docker system info | grep -E "(Server Version|Storage Driver|Cgroup)"
echo

echo "=== Running Containers ==="
docker ps -a
echo

echo "=== Container Health Status ==="
if [ -f "docker-compose.test.yml" ]; then
    docker-compose -f docker-compose.test.yml ps
fi
echo

echo "=== Container Logs (last 50 lines) ==="
for container in postgres redis backend frontend worker; do
    echo "--- $container logs ---"
    docker-compose -f docker-compose.test.yml logs --tail=50 $container 2>/dev/null || echo "Container $container not found"
    echo
done

echo "=== Network Information ==="
docker network ls
echo

echo "=== Port Usage ==="
netstat -tlnp 2>/dev/null | grep -E "(3000|8000|5432|6379)" || ss -tlnp | grep -E "(3000|8000|5432|6379)"
echo

echo "=== Service Health Checks ==="
# PostgreSQL
echo -n "PostgreSQL: "
docker-compose -f docker-compose.test.yml exec -T postgres pg_isready -U test 2>/dev/null && echo "HEALTHY" || echo "UNHEALTHY"

# Redis
echo -n "Redis: "
docker-compose -f docker-compose.test.yml exec -T redis redis-cli ping 2>/dev/null | grep -q PONG && echo "HEALTHY" || echo "UNHEALTHY"

# Backend API
echo -n "Backend API: "
curl -f http://localhost:8000/health 2>/dev/null && echo "HEALTHY" || echo "UNHEALTHY"

# Frontend
echo -n "Frontend: "
curl -f http://localhost:3000 2>/dev/null && echo "HEALTHY" || echo "UNHEALTHY"

# Worker
echo -n "Worker: "
docker-compose -f docker-compose.test.yml exec -T worker celery -A src.workers.celery_app inspect ping 2>/dev/null && echo "HEALTHY" || echo "UNHEALTHY"

echo
echo "=== Recent System Logs ==="
dmesg | tail -20 2>/dev/null || echo "Unable to access system logs"

echo
echo "=== Docker Events (last 5 minutes) ==="
docker events --since "5 minutes ago" --until "1 second ago" 2>/dev/null || echo "No recent events"

echo
echo "=== End of Debug Information ==="
