#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

if [ -d "$PREFIX" ] && [ "$PREFIX" = "/data/data/com.termux/files/usr" ]; then
    TERMUX=true
    echo -e "${CYAN}• Detected Termux environment.${NC}"
else
    TERMUX=false
    echo -e "${CYAN}• Detected Linux environment.${NC}"
fi

echo -e "${YELLOW}• Updating package lists...${NC}"
if $TERMUX; then
    pkg update -y && pkg upgrade -y
    pkg install python python-pip git figlet -y
else
    apt update -y && apt upgrade -y
    apt install python3 python3-pip git figlet -y
fi

if ! command -v pip3 &> /dev/null; then
    echo -e "${YELLOW}• pip3 tidak ditemukan, mencoba menginstalnya...${NC}"
    if $TERMUX; then
        pkg install python-pip -y
    else
        apt install python3-pip -y
    fi

    if ! command -v pip3 &> /dev/null; then
        echo -e "${RED}✖ Gagal menginstal pip3. Memasang pip secara manual...${NC}"
        curl -sS https://bootstrap.pypa.io/get-pip.py -o get-pip.py
        python3 get-pip.py
        rm get-pip.py
    fi
fi

if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}✖ pip tidak dapat diinstal. Periksa lingkungan Anda.${NC}"
    exit 1
else
    echo -e "${GREEN}✔ pip3 berhasil diinstal.${NC}"
fi

echo -e "${YELLOW}• Installing Python libraries...${NC}"
pip3 install --upgrade pip
pip3 install rich requests python-whois dnspython pyfiglet

echo -e "${GREEN}✔ Semua dependensi berhasil diinstal!${NC}"
echo -e "${CYAN}• Anda dapat menjalankan tools dengan perintah:${NC} ${GREEN}python3 main.py atau make run${NC}"