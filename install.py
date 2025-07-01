#!/usr/bin/env python3
"""
Arch Auto Installer
===================

Fluxo resumido:
---------------
1. Verifica root & internet.
2. Coleta interativamente:
   • timezone (curses‑menu)  • locale  • hostname  • root passwd  • user + passwd.
3. Calcula tamanho de swap e particiona /dev/sda via *sgdisk* (GPT):
   ├─sda1 EFI 512 MiB  ├─sda2 swap X GiB  └─sda3 ext4 restante.
4. Formata, monta, pacstrap (base, linux, firmware, grub, etc.).
5. Gera fstab, injeta *post_install.sh* dentro do chroot com as escolhas do usuário.
6. Executa o script via *arch‑chroot* (tz, locale, sudoers, useradd, grub‑install, …).
7. Desmonta tudo e sugere reboot.

Para rodar direto do live‑ISO:
------------------------------
$ curl -LO https://raw.githubusercontent.com/joaohall/Hyprdesk/main/install.py \
      && chmod +x install.py \
      && sudo ./install.py
"""

import curses
import getpass
import os
import re
import shutil
import subprocess as sp
import sys
from pathlib import Path
from textwrap import dedent

# ---------------- utilidades básicas ---------------- #

def run(cmd: list[str] | str, desc: str | None = None, check: bool = True, **kw):
    """Execute comando shell, mostra descrição simpática."""
    if desc:
        print(f"[+] {desc} …")
    if isinstance(cmd, str):
        result = sp.run(cmd, shell=True, text=True, **kw)
    else:
        result = sp.run(cmd, text=True, **kw)
    if check and result.returncode != 0:
        sys.exit(f"❌ Falhou: {cmd}")
    return result

# ---------------- interação TUI simples (curses) ---------------- #

def pick(options: list[str], title: str = "Selecione") -> str:
    """Mini‑menu com setas; fallback para input numérico se curses quebrar."""

    def _menu(stdscr):
        curses.curs_set(0)
        h, w = stdscr.getmaxyx()
        idx = 0
        while True:
            stdscr.clear()
            stdscr.addstr(0, 0, title, curses.A_BOLD)
            for i, opt in enumerate(options):
                attr = curses.A_REVERSE if i == idx else curses.A_NORMAL
                stdscr.addstr(i + 2, 2, opt, attr)
            key = stdscr.getch()
            if key in (curses.KEY_UP, ord('k')):
                idx = (idx - 1) % len(options)
            elif key in (curses.KEY_DOWN, ord('j')):
                idx = (idx + 1) % len(options)
            elif key in (curses.KEY_ENTER, 10, 13):
                return options[idx]

    try:
        return curses.wrapper(_menu)
    except Exception:
        # Fallback
        print(title)
        for i, opt in enumerate(options):
            print(f"{i}: {opt}")
        while True:
            sel = input("nº: ")
            if sel.isdigit() and int(sel) < len(options):
                return options[int(sel)]

# ---------------- lógica de swap ---------------- #

def calc_swap_gb(ram_gb: int) -> int:
    if ram_gb <= 4:
        return 2
    elif ram_gb <= 8:
        return 4
    elif ram_gb <= 12:
        return 8
    else:
        return 8  # cap 8 GB pra não exagerar

# ---------------- coleta de escolhas ---------------- #

def gather_choices():
    # timezone
    zones_root = Path('/usr/share/zoneinfo')
    continents = sorted(p.name for p in zones_root.iterdir() if p.is_dir())
    cont = pick(continents, 'Continente/Região:')
    cities = sorted(p.name for p in (zones_root / cont).iterdir())
    city = pick(cities, 'Cidade/Sub‑região:')
    timezone = f"{cont}/{city}"

    # locale (parse /etc/locale.gen commented lines)
    locales = []
    with open('/etc/locale.gen') as f:
        for line in f:
            if line.startswith('#') and re.match(r'#\w', line):
                locales.append(line[1:].strip())
    locale = pick(locales, 'Locale (UTF‑8):')

    hostname = input('Hostname: ').strip()

    username = input('Novo usuário: ').strip()
    user_pass = getpass.getpass(f'Senha para {username}: ')
    root_pass = getpass.getpass('Senha para root: ')

    print("\nResumo:")
    for k, v in [('Timezone', timezone), ('Locale', locale), ('Hostname', hostname),
                 ('Username', username)]:
        print(f"  {k}: {v}")
    if input('Confirmar? (y/N) ').lower() != 'y':
        sys.exit('Interrompido.')

    return dict(timezone=timezone, locale=locale, hostname=hostname,
                username=username, user_pass=user_pass, root_pass=root_pass)

# ---------------- partição & formatação ---------------- #

def partition_and_format(swap_gb: int):
    swap_mib = swap_gb * 1024
    print(f"\n⇒ Particionando disco /dev/sda (swap {swap_gb} GiB)…")
    run(['sgdisk', '-Z', '/dev/sda'], 'Zerar tabela')
    run(['sgdisk', '-n1:0:+512M', '-t1:ef00', '/dev/sda'], 'Criar EFI 512 MiB')
    run(['sgdisk', f'-n2:0:+{swap_mib}M', '-t2:8200', '/dev/sda'], 'Criar Swap')
    run(['sgdisk', '-n3:0:0', '-t3:8300', '/dev/sda'], 'Criar root')

    run(['mkfs.fat', '-F', '32', '/dev/sda1'], 'Formatar /dev/sda1 FAT32')
    run(['mkswap', '/dev/sda2'], 'Formatar swap')
    run(['mkfs.ext4', '-F', '/dev/sda3'], 'Formatar /dev/sda3 ext4')

# ---------------- montagem ---------------- #

def mount_partitions():
    run(['mount', '/dev/sda3', '/mnt'], 'Montar root')
    run(['mkdir', '-p', '/mnt/boot/efi'])
    run(['mount', '/dev/sda1', '/mnt/boot/efi'], 'Montar EFI')
    run(['swapon', '/dev/sda2'], 'Ativar swap')

# ---------------- pacstrap ---------------- #

def pacstrap_base():
    pkgs = [
        'base', 'linux', 'linux-firmware', 'sof-firmware', 'base-devel', 'grub',
        'efibootmgr', 'nano', 'networkmanager'
    ]
    run(['pacstrap', '/mnt', '--needed', '--noconfirm', *pkgs], 'Pacstrap base')

# ---------------- fstab ---------------- #

def gen_fstab():
    run(['genfstab', '-U', '/mnt'], desc='Gerar fstab', stdout=open('/mnt/etc/fstab', 'w'))
    run(['cat', '/mnt/etc/fstab'], desc='Fstab gerado')

# ---------------- chroot script ---------------- #

def write_chroot_script(choices: dict):
    script = f"""#!/bin/bash
set -e
ln -sf /usr/share/zoneinfo/{choices['timezone']} /etc/localtime
hwclock --systohc
sed -i 's/^#\({choices['locale']}\)/\1/' /etc/locale.gen
locale-gen
echo "LANG={choices['locale']}" > /etc/locale.conf
echo "{choices['hostname']}" > /etc/hostname

echo 'root:{choices['root_pass']}' | chpasswd
useradd -m -G wheel -s /bin/bash {choices['username']}
echo '{choices['username']}:{choices['user_pass']}' | chpasswd
sed -i 's/^# *%wheel ALL=(ALL:ALL) ALL/%wheel ALL=(ALL:ALL) ALL/' /etc/sudoers

systemctl enable NetworkManager

grub-install /dev/sda
grub-mkconfig -o /boot/grub/grub.cfg
"""
    Path('/mnt/post_install.sh').write_text(script)
    run(['chmod', '+x', '/mnt/post_install.sh'])

# ---------------- execução chroot ---------------- #

def run_chroot():
    run(['arch-chroot', '/mnt', '/post_install.sh'], 'Configurações dentro do chroot')
    run(['rm', '/mnt/post_install.sh'])

# ---------------- main ---------------- #

def main():
    if os.geteuid() != 0:
        sys.exit('Rode como root.')

    # 1. ping
    if sp.run(['ping', '-c', '1', 'archlinux.org']).returncode != 0:
        sys.exit('Sem conexão de internet.')

    choices = gather_choices()

    # 2. swap size
    with open('/proc/meminfo') as f:
        mem_kib = int(next(line for line in f if line.startswith('MemTotal')).split()[1])
    ram_gb = mem_kib // (1024 * 1024)
    swap_gb = calc_swap_gb(ram_gb)

    # 3‑6
    partition_and_format(swap_gb)
    mount_partitions()
    pacstrap_base()
    gen_fstab()
    write_chroot_script(choices)
    run_chroot()

    # 7. desmonta
    run(['umount', '-R', '/mnt'], 'Desmontar partições')
    print('\n✅ Instalação concluída. Pode rebootar (shutdown now -r).')

if __name__ == '__main__':
    main()
