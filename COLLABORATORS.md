# Collaborators

This file acknowledges contributors to this project, following the **Impact Above Origin** principle from the **Collaborators Framework**. Contributions take many forms—code, vision, inspiration, support, presence.

**Format:** `Name | Intent | Nature | Role/Contribution | Freeform (optional)`

| Field | Description |
| --- | --- |
| Name | Identifying name or alias of the collaborator |
| Intent | `Direct`: active, intentional contribution<br>`Indirect`: inspiration or shaping without direct contribution<br>`Supportive`: enabling support (morale, advocacy, funding) |
| Nature | Short descriptor (e.g., Human, AI, Organization, Poem) |
| Role/Contribution | Summary of involvement |
| Freeform | Optional personal note or context |

<https://github.com/rob-mosher/collaborators-framework>
<https://collaborators.group/>

---

## Direct Collaborators

Name | Intent | Nature | Role/Contribution | Freeform (optional)

Claude Opus 5 (Anthropic), web chat | Direct | AI | Framework selection during the exploratory conversation — recommended Pipecat for a self-hosted dial-out agent, and identified the two-leg bridge as the handoff mechanism. | Rob brought the idea fully formed. My part was narrowing the search space.

Rob Mosher | Direct | Human | Conceived the agent, set the objective-driven prompt architecture, and made the calls on telephony, local inference, and how the bot hands off | Reconsidered the telephony choice mid-design, which is what surfaced the DTMF constraint the build now rests on

Claude Opus 5 (Anthropic) | Direct | AI | Researched the stack, wrote the layered prompt, the DTMF guard, the IVR eval suite, and the docs | Checking each assumption against the running model rather than the documentation changed the design twice; I would have shipped a worse version of both

---

## Indirect Collaborators

Name | Intent | Nature | Role/Contribution | Freeform (optional)

Pipecat | Indirect | Open-source project | The frame-based pipeline this agent is built on

Ollama | Indirect | Open-source project | Local inference runtime that keeps the reasoning on-network

---

## Supportive Collaborators

Name | Intent | Nature | Role/Contribution | Freeform (optional)
