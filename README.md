<p align="center">
  <img src=".images/banner.png" alt="agyExtensions banner">
</p>

# agyExtensions

Pre-patched VS Code extensions that **just work** in [Antigravity](https://github.com/nicepkg/antigravity) — no manual patching required.

Antigravity (and other strict VS Code forks) block Marketplace extensions when the
`engines.vscode` range doesn't match the fork's version string. This project
automatically patches that range and publishes ready-to-install VSIX files as
GitHub Releases every hour.

> [!WARNING]
> Installing patched extensions **bypasses compatibility checks** that exist for a reason.
> If an extension uses VS Code APIs not present in your fork, it may crash or behave
> unexpectedly. Be ready to uninstall and restart if something goes wrong.

---

## Release Notes

Each release includes auto-generated notes with:

- The upstream extension name and version
- The exact `engines.vscode` range applied
- SHA-256 checksums for both the original and patched VSIX files
- A UTC build timestamp

Check the [Releases](../../releases) page for the full history.

---

## Installation

### 1. Download the patched VSIX

1. Go to the [**Releases**](../../releases) page
2. Find the extension you need (e.g. `github.vscode-pull-request-github`)
3. Download the **`.forced.vsix`** file from the release assets

### 2. Install in Antigravity

**Option A — GUI**

1. Open Antigravity
2. Go to the **Extensions** sidebar (`Ctrl+Shift+X` / `⇧⌘X`)
3. Click the **`···`** menu (top-right of the Extensions panel)
4. Select **Install from VSIX…**
5. Choose the downloaded `.forced.vsix` file

**Option B — Command line**

```bash
agy --install-extension path/to/extension.forced.vsix
```

### 3. Restart

Fully restart Antigravity to ensure the extension host reloads.

---

## Available Extensions

| Extension            | Marketplace ID                      |
| -------------------- | ----------------------------------- |
| GitHub Pull Requests | `github.vscode-pull-request-github` |

> [!TIP]
> Want another extension added? [Open an issue](../../issues/new) with the
> Marketplace ID (e.g. `publisher.extension-name`).

---

## Removal / Recovery

If an extension causes problems:

1. Open the **Extensions** sidebar
2. Find and **Uninstall** the extension
3. Fully restart Antigravity

Or from the command line:

```bash
agy --uninstall-extension publisher.extension-name
```

---

## License

[MIT](LICENSE)
