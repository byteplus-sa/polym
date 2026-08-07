# Provisioning ECS instances

**Mutating. Confirm with the user, then dry-run first.**

## Gather prerequisites (read-only lookups)

```bash
ve ecs DescribeZones                                   # pick ZoneId
ve ecs DescribeInstanceTypes --MaxResults 100          # pick InstanceTypeId (e.g. ecs.g3i.large)
ve ecs DescribeImages --MaxResults 100                 # pick ImageId (filter: --ImageName / --Platform)
ve vpc DescribeVpcs                                    # pick VpcId
ve vpc DescribeSubnets --VpcId vpc-xxx                 # pick SubnetId; USE ITS ZoneId as --ZoneId
ve vpc DescribeSecurityGroups --VpcId vpc-xxx          # pick SG with "Type": "normal" or "default"
                                                       #   NOT "NatGW" (managed SGs fail with
                                                       #   InvalidSecurityGroupType.Malformed)
ve ecs DescribeKeyPairs                                # SSH key (or CreateKeyPair)
```

Field-verified requirements (each missing one is a distinct 400 error):
- `--ZoneId` is required and must match the subnet's zone (`MissingParameter.ZoneId`)
- `--KeyPairName` **or** `--Password` is required (`MissingParameter.PasswordAndKeyPair`)
- SG must be in the same VPC as the subnet and of normal/default type

## Dry run, then create

```bash
ve ecs RunInstances \
  --DryRun true \
  --InstanceName my-instance \
  --InstanceTypeId ecs.g3i.large \
  --ImageId image-xxx \
  --ZoneId ap-southeast-1a \
  --NetworkInterfaces.1.SubnetId subnet-xxx \
  --NetworkInterfaces.1.SecurityGroupIds.1 sg-xxx \
  --Volumes.1.VolumeType ESSD_PL0 --Volumes.1.Size 40 \
  --KeyPairName my-key \
  --InstanceChargeType PostPaid \
  --Count 1 \
  ---profile johor
```

- Dry-run success signal (field-verified): `DryRunOperation: Your request has been validated`, HTTP 412, nothing created. Any other error = fix params first. Then remove `--DryRun true`.
- Note the example lacks `--KeyPairName`/`--Password` — add one (required).
- Public IP: add `--EipAddress.BandwidthMbps 1 --EipAddress.ChargeType PayByTraffic` (or bind an EIP later via `ve vpc` EIP actions).
- Full param list: `ve ecs RunInstances --help` (also `--Password` instead of key pair, `--UserData` base64 cloud-init, spot via `--SpotStrategy`).

## Lifecycle

```bash
ve ecs DescribeInstances --InstanceIds.1 i-xxx        # status: PENDING → RUNNING
ve ecs StopInstance  --InstanceId i-xxx
ve ecs StartInstance --InstanceId i-xxx
ve ecs RebootInstance --InstanceId i-xxx
ve ecs DeleteInstance --InstanceId i-xxx              # DESTRUCTIVE — confirm ID with user, check DeletionProtection
```
