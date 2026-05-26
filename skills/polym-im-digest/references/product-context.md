# Product Context and Focus Order

The digest must be product-aware. Generic chat volume is not enough; sort and
summarize by business relevance.

## Taxonomy

Use three separate fields instead of mixing platform, product, and modality:

| Field | Meaning | Examples |
|-|-|-|
| Product line | Commercial / platform owner bucket | ModelArk / MaaS, Public Cloud / Infra / Ops, Other |
| Offering / model | The concrete product, model, or service discussed | Seedance, Seedream, Seed2.0, Seed-SC, Doubao, DeepSeek, Ark API, Viking |
| Capability / modality | What the customer is trying to do | Video generation, image generation, LoRA, OpenAI-compatible API, copyright review, quota, endpoint integration |

Do not use `AIGC Video / Image` as a product line. It is a capability/modality
tag for Seedance / Seedream and related model workflows.

## Focus Order

1. **ModelArk / MaaS**
2. **Public Cloud / Infra / Ops**
3. **Other / Low Signal**

Within the same priority, `ModelArk / MaaS` renders first. Seedance and
Seedream are usually `ModelArk / MaaS` items with offering/model values:

- `Seedance` for video-generation, r2v, video copyright/safety, video latency,
  and Seedance model access.
- `Seedream` for image-generation, image references, keyframes, image LoRA, and
  Seedream model access.

## Product Line · ModelArk / MaaS

Aliases and signals:

- ModelArk, Ark, 方舟, 方舟平台, Ark API, ArkClaw
- MaaS, model platform, endpoint, EP, model endpoint
- Seedance, Seedream, Seed, Seed 1.x/2.x, Seed-SC
- Doubao, DeepSeek, LLM, reasoning, CoT, TTFT, token budget
- xLLM, Viking, embedding, knowledge base retrieval
- AgentKit, OpenAI-compatible API, Anthropic-compatible API, BaseURL
- quota, concurrency, TPM, RPM, rate limit, 429, access rights, model not found
- copyright review, safety review, rights verification when attached to
  Seedance / Seedream / model generation behavior
- visual quality, generation latency, preview, asset/reference handling, style,
  template, private avatar, upscaler when attached to Seedance / Seedream

Common offering/model mapping:

| Signal | Product line | Offering / model | Capability / modality |
|-|-|-|-|
| Seedance, r2v, video generation, video copyright review | ModelArk / MaaS | Seedance | Video generation / safety |
| Seedream, image generation, image refs, keyframes, LoRA for image | ModelArk / MaaS | Seedream | Image generation / LoRA |
| Seed2.0, Seed-SC, scale support, content pre-filter | ModelArk / MaaS | Seed / Seed-SC | Model runtime / generation |
| Ark API, OpenAI-compatible API, endpoint, provider config | ModelArk / MaaS | Ark API / ModelArk | API integration |
| DeepSeek, Doubao, LLM launch, reasoning, TTFT | ModelArk / MaaS | DeepSeek / Doubao / Seed LLM | LLM inference |
| Viking, embedding, retrieval | ModelArk / MaaS | Viking / embedding | Retrieval / embedding |
| ArkClaw, AgentKit | ModelArk / MaaS | ArkClaw / AgentKit | Agent tooling |

Common owners to infer only as suggestions when no owner is explicit:

- Ark / ModelArk platform: ModelArk oncall lead, Ark API owner, doc owner
- Seedance / Seedream runtime: Seed model owner, ModelArk runtime owner
- Seedance / Seedream safety: Seedance compliance / safety owner
- Ark API compatibility: API compatibility owner, SDK/doc owner
- Viking / embedding: Viking owner + Ark embedding owner

## Product Line · Public Cloud / Infra / Ops

Aliases and signals:

- ECS, TOS, CDN, network, port, security group, billing, IAM, AK/SK
- data freshness, alarms, alerts, stale data, ETL, pipeline, files not ready
- account activation, certificate, domain, HTTPS, region, deployment
- Video Cloud, VOD, MediaLive, RTC, WebSDK, RTM when the discussion is about
  media infrastructure rather than Seedance / Seedream model generation

## Product Line · Other / Low Signal

Use for:

- training announcements with no action
- internal schedule coordination
- generic social chatter
- informational launch notices with no owner/action

## Mandatory Product Coverage Pass

After initial extraction, run a second pass for these terms if they appeared in
raw messages but not in the rendered digest:

- Seedance
- Seedream
- ModelArk / 方舟 / Ark
- Doubao / Seed / DeepSeek
- xLLM
- Viking
- ArkClaw
- AgentKit

For each missing term, decide one of:

- add a priority item
- add a compact appendix item
- explicitly classify it as noise with a one-line reason in internal reasoning

Do not silently drop active Seedance / Seedream / ModelArk / MaaS signals.
