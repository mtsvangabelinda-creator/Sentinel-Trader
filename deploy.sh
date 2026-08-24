#!/bin/bash
set -e

echo "🚀 SentinelTrader - Auto Deployment"
echo "===================================="

# Update system
sudo apt-get update
sudo apt-get install -y curl wget git

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Clone repo
cd /home/ubuntu
git clone https://github.com/YOUR_USERNAME/sentineltrader.git
cd sentineltrader

# Create .env file
cat > .env << 'EOL'
KRAKEN_API_KEY=${KRAKEN_API_KEY}
KRAKEN_API_SECRET=${KRAKEN_API_SECRET}
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
DATABASE_URL=postgresql://sentineltrader_user:sentineltrader_password@postgres:5432/sentineltrader_db
REDIS_URL=redis://redis:6379
ENVIRONMENT=production
LOG_LEVEL=INFO
INITIAL_CAPITAL=300
EOL

# Start services
docker-compose up -d

echo "✅ Deployment complete!"
echo "📊 Access Grafana: http://YOUR_IP:3000"
echo "📝 Check logs: docker-compose logs -f bot"
