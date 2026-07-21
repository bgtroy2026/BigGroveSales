# Sales Portal — user accounts

## Adding someone

Double-click **Manage Users.command**, pick "Add a user", answer the prompts. It asks
for the portal master password once (to unlock the key it hands to the new user), then
for the password you want to give them. Then run **Deploy Portal.command** to publish.

Send the new person their username and password. Nothing is emailed automatically.

## How it works (and what it can't do)

The portal is one static HTML file on GitHub Pages — there is no server, so there is no
central account database that can be checked at sign-in time.

Instead, each user's record carries a copy of the portal's master decryption key,
encrypted under *their own* password. Signing in derives a key from their password,
unwraps the master key, and decrypts the portal. Deleting a user deletes their wrapped
key, so their password stops working on the next deploy.

What follows from that:

- **Accounts take effect on deploy.** Adding or removing someone only reaches people
  after you run Deploy Portal.command.
- **Passwords can't be recovered, only reset.** Nothing stores the password itself.
- **Choose real passwords.** The wrapped keys ship inside the public index.html, so a
  weak password could be attacked offline. Twelve-plus characters, not a dictionary word.
- **The master password still works** as a fallback, with or without a username — you
  can't lock yourself out.
- **"Last sign-in" is per-device**, read from that browser's local storage. There is no
  central log of who signed in. If you want one, set `login_ping` in users.json to a
  Google Apps Script or Formspree URL and each sign-in will POST to it.

## Roles and their default pages

| Role | Pages |
|---|---|
| admin | all |
| manager | all |
| rep | YTD, Tigerhawk, New Placements, Grove, Items, ROS, Overview |
| ops | Inventory, EKOS Invoices, YTD |
| viewer | YTD, Overview |

Page keys: `ytd tigerhawk npl grove inventory ekos pog items ros overview`
(Grove is the mobile map view of Overview and follows Overview's permission.)

You can override the default for any person — option 3 in the menu, or:

```
python3 manage_users.py edit --username jane --pages ytd,tigerhawk,items
python3 manage_users.py edit --username jane --dists "Doll Dist - Des Moines, IA; Doll Dist - Council Bluffs, IA"
```

## Territory

A user's territory is a list of distributor names. Today it shows as a badge next to the
page subtitle and is available to page code as `BGB.inTerritory(name)` and
`BGB.scope(array, fn)`. The dashboards do **not** filter their data by it yet — that's a
separate pass through each page's data layer.

## Request access

The sign-in screen has a "Need access? Request an account" link. Out of the box it opens
a pre-filled email to troy@biggrovebrewery.com. To get form submissions in your inbox
instead, create a free form at formspree.io and put its endpoint in `users.json`:

```json
{ "access_form": "https://formspree.io/f/xxxxxxxx", ... }
```

then run `python3 manage_users.py build` and deploy.

## Command reference

```
python3 manage_users.py list                 # who has an account
python3 manage_users.py pages                # valid page keys and role defaults
python3 manage_users.py add --username jane --name "Jane Doe" --email jane@x.com --role rep
python3 manage_users.py passwd --username jane
python3 manage_users.py edit   --username jane --role manager
python3 manage_users.py remove --username jane
python3 manage_users.py build                # rebuild index.html from users.json
```

`users.json` is the source of truth. It holds no passwords — only wrapped keys.
