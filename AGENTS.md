# Agent Guidelines

## Package Manager Security Restrictions (Minimum Release Age)

This environment enforces strict security policies on package managers to mitigate supply chain attacks by preventing the installation of newly released packages. Additionally, some lifecycle scripts are ignored.

If you encounter errors related to package resolution or installation (such as "not found", "no matching version", or "installation failed" for packages you know exist), it is highly likely due to these configurations:

- **uv**: `exclude-newer = "7 days"`
- **npm**: `min-release-age=7` and `ignore-scripts=true`
- **pnpm**: `minimum-release-age=10080` (7 days)
- **bun**: `minimumReleaseAge = 604800` (7 days)

### How to handle failures:
1. **Fallback to Older Versions:** Do not repeatedly attempt to install the newest possible version if it fails. Fallback to an older, established version that is at least 7 days old.
2. **Post-install Scripts (`ignore-scripts=true`):** Be aware that npm will NOT execute lifecycle scripts (e.g., `postinstall`). This can prevent packages that rely on native binaries or build steps from functioning correctly out of the box. If a package requires these scripts, you may need to run them manually or find an alternative approach.
3. **Do not modify these settings:** These are intentional security measures. Do not attempt to bypass them by changing the global configuration files.
