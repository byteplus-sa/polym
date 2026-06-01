# Changelog

## 0.2.0 - 2026-06-01

- Added `truststore` TLS injection so Ark SDK and Python HTTPS calls can use the OS certificate verifier when available.
- Improved certificate verification failures with actionable guidance instead of a generic request error.
- Fixed Seedance capability matching for dashed model IDs while continuing to accept dotted aliases for compatibility.

## 0.1.0 - 2026-05-18

- Added Polym manifest and smoke test for the imported Seedance generation skill.
