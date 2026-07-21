#!/bin/bash
# Big Grove Sales Portal — user manager (double-click to run)
cd "$(dirname "$0")" || exit 1
python3 -c "import cryptography" 2>/dev/null || { echo "Installing a required library…"; python3 -m pip install --user cryptography || exit 1; }

while true; do
  clear
  echo "=============================================="
  echo "  Big Grove Sales Portal — User Accounts"
  echo "=============================================="
  echo
  python3 manage_users.py list
  echo
  echo "  1) Add a user"
  echo "  2) Reset a user's password"
  echo "  3) Change a user's role / pages / territory"
  echo "  4) Remove a user"
  echo "  5) Show page keys and role defaults"
  echo "  6) Rebuild index.html"
  echo "  q) Quit"
  echo
  read -r -p "Choose: " c
  echo
  case "$c" in
    1) read -r -p "Username (lowercase, no spaces): " u
       read -r -p "Full name: " n
       read -r -p "Email: " e
       read -r -p "Role [admin/manager/rep/ops/viewer] (rep): " r; r=${r:-rep}
       read -r -p "Pages (blank = role default, or 'all', or e.g. ytd,tigerhawk,items): " p
       read -r -p "Territory — distributor names separated by ; (blank = all): " d
       args=(--username "$u" --name "$n" --email "$e" --role "$r")
       [ -n "$p" ] && args+=(--pages "$p")
       [ -n "$d" ] && args+=(--dists "$d")
       python3 manage_users.py add "${args[@]}" ;;
    2) read -r -p "Username: " u; python3 manage_users.py passwd --username "$u" ;;
    3) read -r -p "Username: " u
       read -r -p "New role (blank = leave): " r
       read -r -p "New pages (blank = leave): " p
       read -r -p "New territory (blank = leave): " d
       args=(--username "$u")
       [ -n "$r" ] && args+=(--role "$r")
       [ -n "$p" ] && args+=(--pages "$p")
       [ -n "$d" ] && args+=(--dists "$d")
       python3 manage_users.py edit "${args[@]}" ;;
    4) read -r -p "Username to remove: " u
       read -r -p "Really remove '$u'? (y/n) " yn
       [ "$yn" = "y" ] && python3 manage_users.py remove --username "$u" ;;
    5) python3 manage_users.py pages ;;
    6) python3 manage_users.py build ;;
    q|Q) echo "Remember to run Deploy Portal.command to publish your changes."; exit 0 ;;
  esac
  echo
  read -r -p "Press return to continue…" _
done
