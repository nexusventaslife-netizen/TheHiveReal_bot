# Deployment Guide - Protocol Hive: Titan X

This guide covers deployment options for the Telegram bot.

## 🚀 Quick Start (Local Development)

1. **Install Python 3.11+**
   ```bash
   python3 --version  # Should be 3.11 or higher
   ```

2. **Clone and setup**
   ```bash
   git clone https://github.com/nexusventaslife-netizen/TheHiveReal_bot.git
   cd TheHiveReal_bot
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your actual values
   ```

4. **Setup PostgreSQL**
   ```bash
   # Create database
   createdb hive
   
   # Or with psql
   psql -c "CREATE DATABASE hive;"
   ```

5. **Run the bot**
   ```bash
   python main.py
   ```

## ☁️ Heroku Deployment

1. **Prerequisites**
   - Heroku account
   - Heroku CLI installed

2. **Create Heroku app**
   ```bash
   heroku create your-app-name
   ```

3. **Add PostgreSQL**
   ```bash
   heroku addons:create heroku-postgresql:mini
   ```

4. **Set environment variables**
   ```bash
   heroku config:set TELEGRAM_TOKEN=your_token
   heroku config:set ADMIN_ID=your_id
   heroku config:set POSTBACK_SECRET=your_secret
   heroku config:set OFFERTORO_LINK=your_link
   heroku config:set ADSTERRA_LINK=your_link
   heroku config:set CRYPTO_PAYMENT_ADDRESS=your_address
   ```

5. **Create Procfile**
   ```bash
   echo "web: uvicorn main:app --host 0.0.0.0 --port \$PORT" > Procfile
   ```

6. **Deploy**
   ```bash
   git push heroku main
   ```

7. **Set webhook**
   ```bash
   curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
     -d "url=https://your-app-name.herokuapp.com/telegram/<TOKEN>"
   ```

## 🐳 Docker Deployment

1. **Create Dockerfile**
   ```dockerfile
   FROM python:3.11-slim
   
   WORKDIR /app
   
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   COPY main.py .
   
   CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

2. **Build image**
   ```bash
   docker build -t protocol-hive-titan-x .
   ```

3. **Run container**
   ```bash
   docker run -d \
     -p 8000:8000 \
     -e TELEGRAM_TOKEN=your_token \
     -e DATABASE_URL=your_db_url \
     -e ADMIN_ID=your_id \
     -e POSTBACK_SECRET=your_secret \
     -e OFFERTORO_LINK=your_link \
     -e ADSTERRA_LINK=your_link \
     -e CRYPTO_PAYMENT_ADDRESS=your_address \
     protocol-hive-titan-x
   ```

## 🔧 VPS Deployment (Ubuntu/Debian)

1. **Update system**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. **Install Python and PostgreSQL**
   ```bash
   sudo apt install python3.11 python3-pip postgresql -y
   ```

3. **Setup PostgreSQL**
   ```bash
   sudo -u postgres psql
   CREATE DATABASE hive;
   CREATE USER hiveuser WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE hive TO hiveuser;
   \q
   ```

4. **Clone repository**
   ```bash
   cd /opt
   sudo git clone https://github.com/nexusventaslife-netizen/TheHiveReal_bot.git
   cd TheHiveReal_bot
   sudo pip install -r requirements.txt
   ```

5. **Create systemd service**
   ```bash
   sudo nano /etc/systemd/system/hive-bot.service
   ```
   
   Add:
   ```ini
   [Unit]
   Description=Protocol Hive Titan X Bot
   After=network.target postgresql.service
   
   [Service]
   Type=simple
   User=www-data
   WorkingDirectory=/opt/TheHiveReal_bot
   Environment="TELEGRAM_TOKEN=your_token"
   Environment="DATABASE_URL=postgresql://hiveuser:your_password@localhost/hive"
   Environment="ADMIN_ID=your_id"
   Environment="POSTBACK_SECRET=your_secret"
   Environment="OFFERTORO_LINK=your_link"
   Environment="ADSTERRA_LINK=your_link"
   Environment="CRYPTO_PAYMENT_ADDRESS=your_address"
   ExecStart=/usr/bin/python3 /opt/TheHiveReal_bot/main.py
   Restart=always
   
   [Install]
   WantedBy=multi-user.target
   ```

6. **Start service**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable hive-bot
   sudo systemctl start hive-bot
   ```

7. **Setup Nginx (optional, for webhook)**
   ```bash
   sudo apt install nginx -y
   sudo nano /etc/nginx/sites-available/hive-bot
   ```
   
   Add:
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```
   
   Enable:
   ```bash
   sudo ln -s /etc/nginx/sites-available/hive-bot /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

8. **Setup SSL (recommended)**
   ```bash
   sudo apt install certbot python3-certbot-nginx -y
   sudo certbot --nginx -d your-domain.com
   ```

## 🌐 Railway Deployment

1. **Create account at railway.app**

2. **Create new project from GitHub**

3. **Add PostgreSQL plugin**

4. **Set environment variables in Railway dashboard**

5. **Deploy automatically on push**

## 📱 Setting Telegram Webhook

After deployment, set your webhook:

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -d "url=https://your-domain.com/telegram/<YOUR_BOT_TOKEN>"
```

Verify webhook:
```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

## 🔍 Monitoring

### Check bot status
```bash
curl https://your-domain.com/health
```

### View logs (systemd)
```bash
sudo journalctl -u hive-bot -f
```

### View logs (Heroku)
```bash
heroku logs --tail
```

### View logs (Docker)
```bash
docker logs -f <container_id>
```

## 🔒 Security Checklist

- [ ] Use strong `POSTBACK_SECRET`
- [ ] Keep `TELEGRAM_TOKEN` private
- [ ] Use HTTPS for webhooks
- [ ] Restrict database access
- [ ] Keep dependencies updated
- [ ] Enable PostgreSQL SSL
- [ ] Use firewall rules
- [ ] Regular backups of database

## 🚨 Troubleshooting

### Bot not receiving updates
1. Check webhook is set: `getWebhookInfo`
2. Verify URL is accessible publicly
3. Ensure SSL certificate is valid
4. Check firewall rules

### Database connection fails
1. Verify PostgreSQL is running
2. Check DATABASE_URL format
3. Test connection manually with psql
4. Check user permissions

### OfferToro postback not working
1. Verify postback URL in OfferToro dashboard
2. Check POSTBACK_SECRET matches
3. Ensure /postback endpoint is accessible
4. Review server logs for errors

## 📊 Performance Optimization

1. **Database indexes**
   ```sql
   CREATE INDEX idx_users_telegram_id ON users(telegram_id);
   CREATE INDEX idx_miners_user_id ON miners(user_id);
   CREATE INDEX idx_transactions_user_id ON transactions(user_id);
   ```

2. **Connection pooling**
   - Already implemented with asyncpg
   - Adjust pool size in `init_db()` if needed

3. **Caching**
   - Consider Redis for user sessions
   - Cache frequently accessed data

## 🔄 Updates and Maintenance

```bash
# Pull latest code
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart service
sudo systemctl restart hive-bot
```

## 📞 Support

For deployment issues, consult:
- GitHub Issues
- Telegram Bot API documentation
- FastAPI documentation
- PostgreSQL documentation
