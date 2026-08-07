---
name: polym-bp-cloud
description: "Operate BytePlus/Volcengine cloud via the ve CLI: query and provision ECS, VPC, CDN, API Gateway, CR, VKE, run commands on instances via Cloud Assistant, and use TOS object storage. Trigger: 'list my ECS instances', 've cli'."
metadata:
  requires:
    bins: [ve]
---

# polym-bp-cloud — BytePlus Cloud Ops via `ve`

Operate any BytePlus/Volcengine service from the terminal with the official `ve` CLI (149 services). This skill teaches setup, the universal command pattern, and field-verified recipes. **Default posture: read-only. Any mutating call (create/delete/run/modify) requires explicit user confirmation, and use `--DryRun true` first where supported.**

## When to use this skill
- Query/count cloud resources: ECS, VPC, subnets, security groups, CLB/ALB, EIP, CDN domains, API gateways, CR image registries, CP pipelines, VKE clusters, RDS/Redis, Ark endpoints
- Provision or modify resources (ECS instances, VPCs, …) — with confirmation
- Execute commands on ECS instances without SSH (Cloud Assistant)
- TOS object storage (separate CLI — see `references/tos.md`)
- Set up `ve` or profiles for a new machine/teammate

## When NOT to use this skill
- Ark model *inference* (chat/image/video generation) → `polym-eval-generate-*` skills use API keys, not this CLI
- C360 usage dashboards → `polym-dashboard-watch`

## Setup (one-time per machine)

```bash
ve version || {
  # macOS arm64; other platforms: see github.com/volcengine/volcengine-cli/releases
  gh release download -R volcengine/volcengine-cli -p '*darwin_arm64.tar.gz' -O /tmp/ve.tgz \
    && mkdir -p /tmp/ve_x ~/.local/bin && tar xzf /tmp/ve.tgz -C /tmp/ve_x \
    && cp /tmp/ve_x/ve ~/.local/bin/ && xattr -d com.apple.quarantine ~/.local/bin/ve 2>/dev/null
}
```

Profiles are **per-user** (never commit AK/SK; stored plaintext in `~/.volcengine/config.json`):

```bash
ve configure set --profile johor --mode ak --access-key "$AK" --secret-key "$SK" --region ap-southeast-1
ve configure list                      # show all; `ve configure profile --profile X` switches default
```

**Do NOT pin `--endpoint`** — region-only profiles auto-resolve the endpoint per service. A pinned endpoint (e.g. ark) breaks every other service with `InvalidEndpoint`.

Region IDs (from `ve ecs DescribeRegions`, BytePlus international account):
`ap-southeast-1`=Johor `ap-southeast-3`=Jakarta `cn-hongkong` `cn-beijing` `cn-guangzhou` `cn-shanghai`

## Universal command pattern

```
ve <service> <Action> --<Param> <value> [---profile P] [---region R]
```

- **Fixed flags use TRIPLE dash**: `---profile`, `---region`, `---endpoint`. API params use double dash, PascalCase.
- Arrays: `--InstanceIds.1 i-aaa --InstanceIds.2 i-bbb`. Nested: `--EipAddress.BandwidthMbps 5`.
- **Discovery beats memorization**: `ve --help` lists all services; `ve <svc> --help` lists actions; `ve <svc> <Action> --help` lists every param with its type. Always check `--help` before calling an unfamiliar action.
- Output is JSON. Errors return non-zero exit + a `Code`/`Message`.
- Ark availability varies by region (e.g. not served in ap-southeast-3 — DNS `no such host` is "service not in region", not an auth error).

### Counting resources correctly
`--MaxResults`/`--PageSize` caps at ~100. Prefer the response's `TotalCount`/`TotalNum` field. If absent, page with `NextToken` until empty and count unique IDs — never trust a single page's grep count.

## Quick recipes (all field-verified)

```bash
ve ecs DescribeInstances --MaxResults 100 ---profile johor      # instances (page w/ NextToken)
ve ecs DescribeRegions                                          # authoritative region list
ve vpc DescribeVpcs                                             # VPCs (TotalCount in response)
ve vpc DescribeSubnets --VpcId vpc-xxx
ve cdn ListCdnDomains                                           # CDN domains
ve apig ListGateways                                            # API gateways
ve cr ListRegistries                                            # container image registries
ve cp <Action>                                                  # CI/CD 持续交付 — pipelines, task runs, logs
ve vke ListClusters                                             # Kubernetes clusters
ve ark ListEndpoints                                            # Ark inference endpoints
ve billing <Action>                                             # cost center
```

## References (lazy-loaded)
- `references/provision-ecs.md` — create/modify/delete ECS instances and their prerequisites (image, flavor, subnet, SG). Read before any provisioning.
- `references/cloud-assistant.md` — run shell commands on instances without SSH (base64 contract, invocation lifecycle).
- `references/tos.md` — TOS object storage via `tosutil` (NOT part of `ve`).

## Safety rules
1. Read/list/describe: run freely.
2. Create/modify/delete/invoke: state what will change, get user confirmation, prefer `--DryRun true` first.
3. Never echo secret keys into chat or commit them; reference `~/.volcengine/config.json` by path only.
