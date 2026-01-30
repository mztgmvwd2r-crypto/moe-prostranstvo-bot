#!/bin/bash

# Deployment script for Moe Prostranstvo Telegram Bot
# Usage: ./deploy.sh

set -e

echo "🌿 Deploying Moe Prostranstvo Bot..."

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo "❌ Please do not run as root"
    exit 1
fi

# Check if TELEGRAM_BOT_TOKEN is set
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ TELEGRAM_BOT_TOKEN is not set"
    echo "Please set it with: export TELEGRAM_BOT_TOKEN='your_token'"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt --quiet

# Create data directory if not exists
mkdir -p data

# Set permissions
chmod 700 data
chmod +x bot.py

# Create systemd service file
echo "⚙️  Creating systemd service..."

SERVICE_FILE="/tmp/moe-prostranstvo.service"

cat > $SERVICE_FILE << EOF
[Unit]
Description=Moe Prostranstvo Telegram Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment="TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN"
Environment="OPENAI_API_KEY=$OPENAI_API_KEY"
ExecStart=$(which python3) $(pwd)/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "📋 Service file created at $SERVICE_FILE"
echo ""
echo "To install the service, run:"
echo "  sudo cp $SERVICE_FILE /etc/systemd/system/"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl enable moe-prostranstvo"
echo "  sudo systemctl start moe-prostranstvo"
echo ""
echo "Or run the bot directly with:"
echo "  python3 bot.py"
echo ""
echo "✅ Deployment preparation complete!"
