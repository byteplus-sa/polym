# TOS object storage — via `tosutil` (NOT `ve`)

`ve` has **no `tos` service** — TOS (S3-compatible object storage) ships as a separate CLI, `tosutil`.

> ⚠️ Section written from official docs, not yet field-verified on this team's account. Verify the first run and update this file (docs: https://docs.byteplus.com/en/docs/tos/ → Tools → tosutil).

## Install (macOS arm64)

```bash
curl -fsSL -o ~/.local/bin/tosutil \
  https://tos-tools.tos-cn-beijing.volces.com/darwin_arm64/tosutil   # check docs for current URL
chmod +x ~/.local/bin/tosutil && xattr -d com.apple.quarantine ~/.local/bin/tosutil 2>/dev/null
```

## Configure (same AK/SK as `ve`, per-user)

```bash
tosutil config -i "$AK" -k "$SK" -e tos-ap-southeast-1.bytepluses.com -re ap-southeast-1
```

Endpoint pattern: `tos-<region>.bytepluses.com` (BytePlus intl) / `tos-<region>.volces.com` (Volcengine CN).

## Common ops

```bash
tosutil ls                                    # list buckets
tosutil ls tos://my-bucket/prefix/            # list objects
tosutil cp local.txt tos://my-bucket/key.txt  # upload
tosutil cp tos://my-bucket/key.txt ./         # download
tosutil cp -r ./dir tos://my-bucket/dir/      # recursive
tosutil rm tos://my-bucket/key.txt            # DESTRUCTIVE — confirm first
tosutil sync ./dir tos://my-bucket/dir/       # sync (large trees; resumable)
```

TOS is S3-compatible, so `aws s3 --endpoint-url https://tos-<region>.bytepluses.com` also works if awscli is already installed.
