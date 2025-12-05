#!/bin/bash
# Setup ansible-pull on target nodes

set -e

echo "Setting up ansible-pull on $(hostname)..."

# Install ansible if not present
if ! command -v ansible-pull &> /dev/null; then
    echo "Installing Ansible..."
    if [ -f /etc/debian_version ]; then
        apt update
        apt install -y ansible git
    elif [ -f /etc/redhat-release ]; then
        dnf install -y ansible git
    else
        echo "Unsupported OS"
        exit 1
    fi
fi

# Create ansible-pull directories
mkdir -p /opt/ansible-pull
mkdir -p /var/log/ansible-pull
mkdir -p /etc/ansible-pull

# Copy configuration
if [ -f /vagrant/ansible-pull/config.yml ]; then
    cp /vagrant/ansible-pull/config.yml /etc/ansible-pull/config.yml
else
    # Create minimal config
    cat > /etc/ansible-pull/config.yml << 'CONFIGEOF'
---
ansible_pull:
  repository: /opt/git/repos/config-drift.git
  playbook: playbooks/webserver-deploy.yml
  inventory: localhost,
  log_file: /var/log/ansible-pull.log
CONFIGEOF
fi

# Create ansible-pull wrapper script
cat > /usr/local/bin/run-ansible-pull << 'SCRIPTEOF'
#!/bin/bash
# Ansible-pull wrapper with logging and notification

LOG_FILE="/var/log/ansible-pull/run-$(date +%Y%m%d-%H%M%S).log"
CONFIG_FILE="/etc/ansible-pull/config.yml"

echo "=== Ansible-Pull Run $(date) ===" | tee -a "$LOG_FILE"

# Load configuration
if [ -f "$CONFIG_FILE" ]; then
    REPO=$(grep -E '^\s*repository:' "$CONFIG_FILE" | awk '{print $2}')
    PLAYBOOK=$(grep -E '^\s*playbook:' "$CONFIG_FILE" | awk '{print $2}')
    BRANCH=$(grep -E '^\s*branch:' "$CONFIG_FILE" | awk '{print $2}' || echo "main")
else
    REPO="/opt/git/repos/config-drift.git"
    PLAYBOOK="playbooks/webserver-deploy.yml"
    BRANCH="main"
fi

# Run ansible-pull
echo "Repository: $REPO" | tee -a "$LOG_FILE"
echo "Playbook: $PLAYBOOK" | tee -a "$LOG_FILE"
echo "Branch: $BRANCH" | tee -a "$LOG_FILE"

ansible-pull \
  -U "$REPO" \
  -C "$BRANCH" \
  --purge \
  --only-if-changed \
  --accept-host-key \
  --verbose \
  "$PLAYBOOK" 2>&1 | tee -a "$LOG_FILE"

EXIT_CODE=${PIPESTATUS[0]}

echo "Exit code: $EXIT_CODE" | tee -a "$LOG_FILE"
echo "=== Run completed $(date) ===" | tee -a "$LOG_FILE"

# Check for changes
if tail -20 "$LOG_FILE" | grep -q "changed="; then
    CHANGES=$(tail -20 "$LOG_FILE" | grep "changed=" | tail -1)
    echo "Changes detected: $CHANGES" | tee -a "$LOG_FILE"
    
    # Send notification if configured
    if [ -f /usr/local/bin/notify-drift.sh ]; then
        /usr/local/bin/notify-drift.sh "ansible-pull" "Changes applied: $CHANGES"
    fi
fi

exit $EXIT_CODE
SCRIPTEOF

chmod +x /usr/local/bin/run-ansible-pull

# Create systemd service for ansible-pull
cat > /etc/systemd/system/ansible-pull.service << 'SERVICEEOF'
[Unit]
Description=Ansible Pull - Configuration Drift Remediation
After=network.target

[Service]
Type=oneshot
User=root
ExecStart=/usr/local/bin/run-ansible-pull
Environment=PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=ANSIBLE_CONFIG=/etc/ansible/ansible.cfg

# Logging
StandardOutput=journal
StandardError=journal

# Security
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
SERVICEEOF

# Create systemd timer for ansible-pull
cat > /etc/systemd/system/ansible-pull.timer << 'TIMEREOF'
[Unit]
Description=Run ansible-pull periodically
Requires=ansible-pull.service

[Timer]
# Run every 30 minutes with randomized delay
OnCalendar=*-*-* *:0/30:00
RandomizedDelaySec=300
Persistent=true

[Install]
WantedBy=timers.target
TIMEREOF

# Reload systemd and enable timer
systemctl daemon-reload
systemctl enable ansible-pull.timer
systemctl start ansible-pull.timer

echo "Ansible-pull setup complete"
echo "Service: ansible-pull.service"
echo "Timer: ansible-pull.timer (runs every 30 minutes)"
echo "Logs: /var/log/ansible-pull/"
echo "Manual run: run-ansible-pull"
