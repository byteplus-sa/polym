# Cloud Assistant — run commands on ECS without SSH

Executes shell (Linux) / PowerShell-Bat (Windows) on instances via the in-guest agent. **Executing a command mutates the instance — confirm with the user what will run and where.**

## Contract
- `--CommandContent` must be **base64-encoded**; result `Output` is **base64-encoded** — decode both ways.
- Agent must be installed & running on the instance (preinstalled on recent official images).

## Flow

```bash
# 1. Agent status (read-only)
ve ecs DescribeCloudAssistantStatus --InstanceIds.1 i-xxx ---profile johor
# Status: Running → good. Not installed → ve ecs InstallCloudAssistant --InstanceIds.1 i-xxx

# 2. Run ad-hoc command (returns InvocationId)
ve ecs RunCommand \
  --InstanceIds.1 i-xxx \
  --Type Shell \
  --Name adhoc-check \
  --CommandContent "$(printf 'df -h\nuptime' | base64)" \
  --Timeout 60 \
  ---profile johor

# 3. Poll status then fetch output
ve ecs DescribeInvocationInstances --InvocationId ivk-xxx     # InvocationStatus: Running → Success/Failed
ve ecs DescribeInvocationResults  --InvocationId ivk-xxx \
  | grep -oE '"Output": *"[^"]*"' | cut -d'"' -f4 | base64 -d
```

## Reusable commands

```bash
ve ecs CreateCommand --Name deploy-check --Type Shell --CommandContent "$(base64 < script.sh)"
ve ecs InvokeCommand --CommandId cmd-xxx --InstanceIds.1 i-xxx
ve ecs DescribeCommands                                       # list saved commands
ve ecs StopInvocation --InvocationId ivk-xxx                  # kill a running task
```

Notes: `--WorkingDir`, `--Username`, `--EnableParameter` (template variables) available — see `ve ecs RunCommand --help`. Exit code of the remote script is in the invocation result (`ExitCode`).
