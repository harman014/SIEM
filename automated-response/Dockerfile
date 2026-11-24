FROM python:3.11-slim

# Install iptables for firewall management
RUN apt-get update && \
    apt-get install -y iptables iproute2 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-u", "main.py"]
