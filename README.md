# agyExtensions

A tiny, standalone Python tool + an hourly GitHub Action that:

- fetches the latest VSIX for a VS Code Marketplace extension
- patches `extension/package.json -> engines.vscode` to a broader semver range (default: `>=1.0.0`)
- republishes the patched artifact as a GitHub Release **only when upstream version changes**

This is intended for strict VS Code forks (e.g. Antigravity) that refuse to enable extensions due to engine gating.

> [!WARNING]
> This may break your Antigravity install or destabilize your editor.
> You are bypassing compatibility checks that exist for a reason.
> Proceed with caution, and be ready to remove the extension if the extension host starts crashing or behaving oddly.

## What gets released

Each new upstream extension version produces a GitHub Release that includes:

- the **original** upstream VSIX
- the **forced** VSIX (patched `engines.vscode` range)
- `meta.json` containing:
  - extension id + upstream version
  - patched `engines.vscode` range
  - SHA256 checksums for both VSIX files
  - build timestamp (UTC)

## Local usage

Patch and output a forced VSIX:

```bash
python3 force_install_vsix.py github.vscode-pull-request-github \
  --engine ">=1.0.0" \
  --out-dir dist \
  --notes \
  --meta-json dist/meta.json
```

Optionally attempt install via Antigravity CLI:

```bash
python3 force_install_vsix.py github.vscode-pull-request-github \
  --engine ">=1.0.0" \
  --install \
  --agy agy
```

## GitHub Action (hourly)

The workflow runs on a cron schedule:

- `0 * * * *` (hourly, UTC)

It will create a release only if a tag named:

```
<publisher.extension>-<upstreamVersion>
```

does not already exist.

### Track more extensions

Edit `.github/workflows/hourly-force-vsix.yml` and add entries under:

```yaml
matrix:
  extension_id:
    - github.vscode-pull-request-github
```

### Change the engine range

In the workflow, edit:

```yaml
ENGINE_RANGE: ">=1.0.0"
```

## Removal / recovery

If the extension host is unhappy:

- disable/uninstall from the Extensions UI, or
- remove the extension from Antigravity’s extensions directory (location varies by build)
- restart the editor completely
