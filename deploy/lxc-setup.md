# LXC Deployment

Target container:

- Ubuntu 24.04 LTS
- 8 vCPU
- 16 GB RAM
- 100 GB SSD

Install system packages:

```bash
apt update
apt install -y python3.12 python3.12-venv python3-pip ffmpeg nginx nodejs npm
npm install -g pm2
```

Create service user and storage:

```bash
useradd --system --create-home --shell /usr/sbin/nologin whisper
mkdir -p /opt/whisper-transcribe /data/sessions
chown -R whisper:whisper /opt/whisper-transcribe /data
```

Install the app:

```bash
cd /opt/whisper-transcribe
chmod +x deploy.sh
WHISPER_DATA_DIR=/data ./deploy.sh
```

Enable PM2 startup and install proxy:

```bash
pm2 startup systemd
pm2 save
cp deploy/nginx.conf /etc/nginx/sites-available/whisper-transcribe
ln -s /etc/nginx/sites-available/whisper-transcribe /etc/nginx/sites-enabled/whisper-transcribe
nginx -t
systemctl restart nginx
```

The first transcription request downloads and initializes `large-v3-turbo`, so expect a slower cold start.
