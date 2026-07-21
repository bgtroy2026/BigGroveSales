#!/usr/bin/env python3
"""
Big Grove Sales Portal — user manager.

The portal is a single static index.html, so there is no server to hold accounts.
Instead every user gets their own password, and their record stores a copy of the
portal's master decryption key wrapped (encrypted) under that password. Signing in
unwraps the key and decrypts the portal. Deleting a user removes their wrapped key,
so their password stops working on the next deploy.

Passwords are never stored anywhere — only the wrapped key blob, which is useless
without the password. If someone forgets theirs, set a new one.

Usage
  python3 manage_users.py list
  python3 manage_users.py add     --username jane --name "Jane Doe" --email jane@x.com --role rep
  python3 manage_users.py edit    --username jane --pages ytd,tigerhawk,items --dists "Doll Dist - Des Moines, IA"
  python3 manage_users.py passwd  --username jane
  python3 manage_users.py remove  --username jane
  python3 manage_users.py build            # rebuild index.html from users.json
  python3 manage_users.py pages            # list valid page keys
"""

import argparse, base64, getpass, json, os, re, secrets, sys, datetime
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(HERE, "index.html")
USERS_JSON = os.path.join(HERE, "users.json")
TEMPLATE = os.path.join(HERE, "tools", "login_template.html")

PAGES = {
    "ytd": "YTD Sales",
    "tigerhawk": "Tigerhawk",
    "npl": "New Placements",
    "grove": "The Grove (map)",
    "inventory": "Inventory",
    "ekos": "EKOS Invoices",
    "pog": "Planograms",
    "items": "Daily Item Sales",
    "ros": "Rate of Sale",
    "overview": "H1 Sales Overview",
}

ROLE_PAGES = {
    "admin":   "*",
    "manager": "*",
    "rep":     ["ytd", "tigerhawk", "npl", "grove", "items", "ros", "overview"],
    "ops":     ["inventory", "ekos", "ytd"],
    "viewer":  ["ytd", "overview"],
}

# ---------------------------------------------------------------- crypto

def pbkdf2(pw: str, salt: bytes, iters: int) -> bytes:
    return PBKDF2HMAC(algorithm=hashes.SHA256(), length=32,
                      salt=salt, iterations=iters).derive(pw.encode())


def b64(b: bytes) -> str:
    return base64.b64encode(b).decode()


def ub64(s: str) -> bytes:
    return base64.b64decode(s)


def wrap_master(master_key: bytes, user_pw: str, iters: int = 300000):
    """Encrypt the master key under a key derived from the user's password."""
    salt = secrets.token_bytes(16)
    iv = secrets.token_bytes(12)
    uk = pbkdf2(user_pw, salt, iters)
    blob = AESGCM(uk).encrypt(iv, master_key, None)
    return b64(salt), iters, f"{b64(iv)}:{b64(blob)}"


def unwrap_master(rec: dict, user_pw: str) -> bytes:
    iv_b64, blob_b64 = rec["w"].split(":")
    uk = pbkdf2(user_pw, ub64(rec["s"]), rec.get("it", 300000))
    return AESGCM(uk).decrypt(ub64(iv_b64), ub64(blob_b64), None)

# ---------------------------------------------------------------- index.html

def read_index():
    with open(INDEX, "r", encoding="utf-8") as f:
        lines = f.read().split("\n")
    enc = data_line = logo = None
    for l in lines:
        if l.startswith("const ENC="):
            enc = json.loads(re.sub(r"(\w+):", r'"\1":', l[len("const ENC="):].rstrip(";")))
        elif l.startswith("const DATA="):
            data_line = l
        elif logo is None and 'src="data:image/png;base64' in l and "<img" in l:
            logo = l
    if not (enc and data_line and logo):
        sys.exit("Could not parse index.html (missing ENC, DATA, or logo).")
    return lines, enc, data_line, logo


def master_key_from_password(enc, pw) -> bytes:
    return pbkdf2(pw, ub64(enc["salt"]), enc["iter"])


def verify_master(enc, data_line, pw) -> bytes:
    """Derive the master key and prove it decrypts the portal."""
    key = master_key_from_password(enc, pw)
    data = data_line[len('const DATA="'):].rstrip(";").rstrip('"')
    AESGCM(key).decrypt(ub64(enc["iv"]), ub64(data), None)
    return key

# ---------------------------------------------------------------- user store

def load_users() -> dict:
    if not os.path.exists(USERS_JSON):
        return {"users": [], "access_form": "", "login_ping": ""}
    with open(USERS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def save_users(db: dict):
    with open(USERS_JSON, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2)
        f.write("\n")


def find(db, username):
    u = username.strip().lower()
    for r in db["users"]:
        if r["u"].lower() == u:
            return r
    return None


def parse_pages(s, role):
    if s is None:
        return ROLE_PAGES.get(role, ["overview"])
    s = s.strip()
    if s in ("*", "all"):
        return "*"
    keys = [k.strip() for k in s.split(",") if k.strip()]
    bad = [k for k in keys if k not in PAGES]
    if bad:
        sys.exit(f"Unknown page key(s): {', '.join(bad)}\nValid: {', '.join(PAGES)}")
    return keys


def parse_dists(s):
    if s is None or s.strip() in ("*", "all", ""):
        return "*"
    return [d.strip() for d in s.split(";") if d.strip()]

# ---------------------------------------------------------------- build

def build(db, master_pw=None):
    lines, enc, data_line, logo = read_index()
    with open(TEMPLATE, "r", encoding="utf-8") as f:
        tpl = f.read()

    records = []
    for r in db["users"]:
        records.append({k: r[k] for k in ("u", "n", "e", "r", "p", "d", "s", "it", "w") if k in r})

    rev = datetime.datetime.now().strftime("%m%d") + "u"
    out = (tpl
           .replace("{LOGO}", logo)
           .replace("{ENC}", f"const ENC={json.dumps(enc, separators=(',', ':'))};")
           .replace("{DATA}", data_line)
           .replace("{USERS}", json.dumps(records, separators=(",", ":")))
           .replace("{ACCESS_FORM}", json.dumps(db.get("access_form", "")))
           .replace("{LOGIN_PING}", json.dumps(db.get("login_ping", "")))
           .replace("{REV}", rev))

    with open(INDEX, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"Rebuilt index.html — {len(records)} user account(s), rev {rev}")

# ---------------------------------------------------------------- commands

def cmd_list(args):
    db = load_users()
    if not db["users"]:
        print("No users yet. The master password still works.")
        return
    print(f"{'USERNAME':<14}{'NAME':<22}{'ROLE':<10}{'PAGES':<34}TERRITORY")
    print("-" * 104)
    for r in db["users"]:
        p = "all" if r["p"] == "*" else ",".join(r["p"])
        d = "all" if r["d"] == "*" else "; ".join(r["d"])
        print(f"{r['u']:<14}{(r.get('n') or ''):<22}{r['r']:<10}{p[:32]:<34}{d[:40]}")


def cmd_pages(args):
    print("Page keys you can grant:\n")
    for k, v in PAGES.items():
        print(f"  {k:<12}{v}")
    print("\nRole defaults:")
    for k, v in ROLE_PAGES.items():
        print(f"  {k:<10}{'all pages' if v == '*' else ','.join(v)}")


def cmd_add(args):
    db = load_users()
    if find(db, args.username):
        sys.exit(f"User '{args.username}' already exists — use edit or passwd.")
    lines, enc, data_line, logo = read_index()
    master_pw = args.master or getpass.getpass("Portal master password: ")
    try:
        mk = verify_master(enc, data_line, master_pw)
    except Exception:
        sys.exit("That master password does not unlock the portal.")
    pw = args.password or getpass.getpass(f"New password for {args.username}: ")
    if len(pw) < 8:
        sys.exit("Password must be at least 8 characters.")
    s, it, w = wrap_master(mk, pw)
    db["users"].append({
        "u": args.username.strip(),
        "n": args.name or args.username,
        "e": args.email or "",
        "r": args.role,
        "p": parse_pages(args.pages, args.role),
        "d": parse_dists(args.dists),
        "s": s, "it": it, "w": w,
        "created": datetime.date.today().isoformat(),
    })
    save_users(db)
    build(db)
    print(f"Added {args.username} ({args.role}). Send them their username and password.")


def cmd_edit(args):
    db = load_users()
    r = find(db, args.username)
    if not r:
        sys.exit(f"No user '{args.username}'.")
    if args.name:
        r["n"] = args.name
    if args.email:
        r["e"] = args.email
    if args.role:
        r["r"] = args.role
        if args.pages is None:
            r["p"] = ROLE_PAGES.get(args.role, r["p"])
    if args.pages is not None:
        r["p"] = parse_pages(args.pages, r["r"])
    if args.dists is not None:
        r["d"] = parse_dists(args.dists)
    save_users(db)
    build(db)
    print(f"Updated {r['u']}.")


def cmd_passwd(args):
    db = load_users()
    r = find(db, args.username)
    if not r:
        sys.exit(f"No user '{args.username}'.")
    lines, enc, data_line, logo = read_index()
    master_pw = args.master or getpass.getpass("Portal master password: ")
    try:
        mk = verify_master(enc, data_line, master_pw)
    except Exception:
        sys.exit("That master password does not unlock the portal.")
    pw = args.password or getpass.getpass(f"New password for {r['u']}: ")
    if len(pw) < 8:
        sys.exit("Password must be at least 8 characters.")
    r["s"], r["it"], r["w"] = wrap_master(mk, pw)
    save_users(db)
    build(db)
    print(f"Password reset for {r['u']}.")


def cmd_remove(args):
    db = load_users()
    r = find(db, args.username)
    if not r:
        sys.exit(f"No user '{args.username}'.")
    db["users"] = [x for x in db["users"] if x is not r]
    save_users(db)
    build(db)
    print(f"Removed {args.username}. Their password stops working once you deploy.")


def cmd_build(args):
    build(load_users())


def main():
    ap = argparse.ArgumentParser(description="Manage Big Grove Sales Portal accounts")
    sp = ap.add_subparsers(dest="cmd", required=True)

    sp.add_parser("list").set_defaults(func=cmd_list)
    sp.add_parser("pages").set_defaults(func=cmd_pages)
    sp.add_parser("build").set_defaults(func=cmd_build)

    a = sp.add_parser("add")
    a.add_argument("--username", required=True)
    a.add_argument("--name")
    a.add_argument("--email")
    a.add_argument("--role", default="rep", choices=list(ROLE_PAGES))
    a.add_argument("--pages", help="comma-separated page keys, or 'all'")
    a.add_argument("--dists", help="semicolon-separated distributor names, or 'all'")
    a.add_argument("--password")
    a.add_argument("--master")
    a.set_defaults(func=cmd_add)

    e = sp.add_parser("edit")
    e.add_argument("--username", required=True)
    e.add_argument("--name")
    e.add_argument("--email")
    e.add_argument("--role", choices=list(ROLE_PAGES))
    e.add_argument("--pages")
    e.add_argument("--dists")
    e.set_defaults(func=cmd_edit)

    p = sp.add_parser("passwd")
    p.add_argument("--username", required=True)
    p.add_argument("--password")
    p.add_argument("--master")
    p.set_defaults(func=cmd_passwd)

    r = sp.add_parser("remove")
    r.add_argument("--username", required=True)
    r.set_defaults(func=cmd_remove)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
