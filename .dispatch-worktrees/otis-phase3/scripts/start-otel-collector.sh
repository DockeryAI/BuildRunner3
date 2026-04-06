#!/bin/bash
# Start OpenTelemetry Collector for BuildRunner monitoring

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COLLECTOR_VERSION="0.91.0"
COLLECTOR_DIR="$PROJECT_DIR/.otel-collector"
COLLECTOR_BINARY="$COLLECTOR_DIR/otelcol"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}BuildRunner OpenTelemetry Collector Manager${NC}"
echo "========================================="

# Check if collector is already running
if pgrep -f "otelcol.*buildrunner" > /dev/null; then
    echo -e "${YELLOW}OpenTelemetry Collector is already running${NC}"
    echo "PID: $(pgrep -f 'otelcol.*buildrunner')"
    echo ""
    echo "To stop it, run: pkill -f 'otelcol.*buildrunner'"
    exit 0
fi

# Download collector if not present
if [ ! -f "$COLLECTOR_BINARY" ]; then
    echo -e "${YELLOW}OpenTelemetry Collector not found. Downloading...${NC}"

    mkdir -p "$COLLECTOR_DIR"

    # Detect OS and architecture
    OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
    ARCH="$(uname -m)"

    if [ "$ARCH" = "x86_64" ]; then
        ARCH="amd64"
    elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
        ARCH="arm64"
    fi

    DOWNLOAD_URL="https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v${COLLECTOR_VERSION}/otelcol_${COLLECTOR_VERSION}_${OS}_${ARCH}.tar.gz"

    echo "Downloading from: $DOWNLOAD_URL"

    curl -L -o "$COLLECTOR_DIR/otelcol.tar.gz" "$DOWNLOAD_URL"
    tar -xzf "$COLLECTOR_DIR/otelcol.tar.gz" -C "$COLLECTOR_DIR" otelcol
    rm "$COLLECTOR_DIR/otelcol.tar.gz"
    chmod +x "$COLLECTOR_BINARY"

    echo -e "${GREEN}✓ Collector downloaded successfully${NC}"
fi

# Check if config file exists
CONFIG_FILE="$PROJECT_DIR/otel-collector-config.yaml"
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}Error: Configuration file not found at $CONFIG_FILE${NC}"
    exit 1
fi

# Check if Datadog API key is set
if [ -z "$DD_API_KEY" ]; then
    # Try to load from .env file
    if [ -f "$PROJECT_DIR/.env" ]; then
        export $(grep -E '^DD_API_KEY=' "$PROJECT_DIR/.env" | xargs)
    fi

    if [ -z "$DD_API_KEY" ]; then
        echo -e "${RED}Error: DD_API_KEY not set${NC}"
        echo "Please set the DD_API_KEY environment variable or add it to your .env file"
        exit 1
    fi
fi

# Start the collector
echo -e "${GREEN}Starting OpenTelemetry Collector...${NC}"
echo "Configuration: $CONFIG_FILE"
echo "Datadog Site: ${DD_SITE:-us5.datadoghq.com}"
echo ""

# Run in background and log to file
LOG_FILE="$PROJECT_DIR/.buildrunner/logs/otel-collector.log"
mkdir -p "$(dirname "$LOG_FILE")"

nohup "$COLLECTOR_BINARY" --config "$CONFIG_FILE" > "$LOG_FILE" 2>&1 &
COLLECTOR_PID=$!

# Wait a moment to check if it started successfully
sleep 2

if ps -p $COLLECTOR_PID > /dev/null; then
    echo -e "${GREEN}✓ OpenTelemetry Collector started successfully${NC}"
    echo "PID: $COLLECTOR_PID"
    echo "Logs: $LOG_FILE"
    echo ""
    echo "Endpoints:"
    echo "  - OTLP HTTP: http://localhost:4318"
    echo "  - OTLP gRPC: localhost:4317"
    echo ""
    echo "To stop: kill $COLLECTOR_PID"

    # Save PID for later
    echo $COLLECTOR_PID > "$PROJECT_DIR/.otel-collector/collector.pid"
else
    echo -e "${RED}Failed to start OpenTelemetry Collector${NC}"
    echo "Check logs at: $LOG_FILE"
    tail -20 "$LOG_FILE"
    exit 1
fi