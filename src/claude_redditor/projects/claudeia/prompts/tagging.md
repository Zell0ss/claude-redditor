# PROMPT: Sistema de Etiquetado Multi-Tier para ClaudeRedditor

## INSTRUCCIÓN GENERAL

Clasifica los siguientes artículos usando un sistema de 9 Tiers + scoring + clusters.

**Contexto del proyecto**: {topic}

## ARTÍCULOS A CLASIFICAR

{posts_json}

---

## FORMATO DE RESPUESTA

Devuelve un **array JSON** con un objeto por cada `post_id` en los artículos proporcionados.

**IMPORTANTE**:
- NO uses backticks (para poder convertirlo a diccionario en Python directamente)
- Cada objeto debe tener: `post_id`, `tier_tags` (objeto con tier1-tier9), `clusters` (array), `scoring` (número)
- Si no aplica un Tier, déjalo vacío []
- Usa las etiquetas sugeridas, pero puedes crear nuevas si es absolutamente necesario

---

## TIER 1: IDENTIFICADORES

**Pregunta**: ¿Qué entidades específicas son el sujeto principal?

**Etiquetas disponibles**:
```
anthropic | openai | cloudflare | ai2 | google | meta | deepmind | microsoft |
claude | claude-code | chatgpt | gemini | gpt-4 | llama |
cloudflare-workers | matrix-protocol | zork | slack | figma | asana | github |  qwen | glm
```

---

## TIER 2: CATEGORÍA TÉCNICA

**Pregunta**: ¿En qué dominio técnico/funcional se inscribe?

**Instrucción**: Elige 1-2 máximo.

**Etiquetas disponibles**:
```
code-generation | code-execution | code-quality | refactoring | testing | debugging |
infrastructure | cloud-native | containerization | package-management | api-integration |
ai-capabilities | nlp-integration | reasoning | planning | multi-turn-planning | autonomous-agents |
real-time-visualization | action-execution | multi-platform-orchestration | workflow-automation |
interactive-fiction | legacy-modernization | system-access | data-retrieval
```

---

## TIER 3: PATRÓN/SIGNAL

**Pregunta**: ¿Cuál es el patrón o hallazgo más interesante?

**Instrucción**: Múltiples OK. Estos tags generan "clusters de valor".

**Etiquetas disponibles**:
```
BRECHAS:
gap-documentation | undocumented-capabilities | emergent-behavior | quality-assurance-failure

DEMOCRATIZACIÓN:
democratization | open-source | accessibility

DISCOVERY:
community-discovery | user-research | capability-expansion

EXPERIENCIA:
friction-elimination | developer-experience-improvement | user-experience-enhancement

TRANSPARENCIA:
transparency-in-action | explainability

METODOLOGÍA:
human-in-the-loop | methodology-over-speed | methodology-first

COMPETICIÓN:
competitive-differentiation | vendor-feature-arms-race | competitive-landscape

SEGURIDAD:
risk-mitigation | safety-validation | safety-concerns

OTROS:
novel-integration | legacy-bridge
```

---

## TIER 4: IMPLICACIÓN

**Pregunta**: ¿Cuál es el impacto o significado más amplio?

**Instrucción**: 1-2 máximo.

**Etiquetas disponibles**:
```
trust-deficit | vendor-credibility |
legacy-modernization-viable | business-model-shift |
safety-alignment | characterization-gap | integration-depth-increasing |
economic-value | market-positioning | lock-in-strategy
```

---

## TIER 5: IMPLEMENTACIÓN/STACK

### 5A) Herramientas & lenguajes

**tool:X** (la herramienta/plataforma):
```
tool:claude-code | tool:chatgpt-containers | tool:tambo | tool:[NEW: X]
```

**language:X** (lenguaje de programación):
```
language:python | language:typescript | language:rust | language:go | language:javascript | language:bash
```
si tienes que crear una nueva etiqueta de lenguaje, usa "language:" seguido del nombre, e.g. "language:python" 

**framework:X**:
```
framework:django | framework:fastapi | framework:flask 
```
si necesitas crear una nueva etiqueta de framework, usa "framework:" seguido del nombre, e.g. "framework:django" 

---

### 5B) SO & Arquitectura

**os:X** (Sistema Operativo):
```
os:macos | os:windows | os:linux | os:cross-platform | os:browser-based | 
os:mobile-ios | os:mobile-android | os:web-only
```

**arch:X** (CPU Architecture):
```
arch:arm64 | arch:x86 | arch:arch-agnostic
```

---

### 5C) Servidor/MCP

**server:X** (tipo de servicio):
```
server:mcp | server:api-rest | server:websocket | server:grpc | server:cli-tool | 
server:daemon | server:browser-extension | server:desktop-app | server:mobile-app | server:none
```

**mcp:X** (si es MCP, en qué lenguaje):
```
mcp:python | mcp:nodejs | mcp:typescript | mcp:rust | mcp:go 
Si tienes que crear una nueva etiqueta de lenguaje, usa "mcp:" seguido del nombre, e.g. "mcp:python"
```

**process:X**:
```
process:single-instance | process:multi-instance | process:distributed | process:containerized
```

---

### 5D) Hardware

**cpu:X**:
```
cpu:minimal | cpu:modest | cpu:standard | cpu:powerful
```

**memory:X**:
```
memory:minimal | memory:modest | memory:standard | memory:high
```

**gpu:X**:
```
gpu:none | gpu:optional | gpu:required | gpu:type:nvidia | gpu:type:amd | gpu:type:apple
```

**storage:X**:
```
storage:minimal | storage:modest | storage:standard | storage:high
```

**hardware:X** (caso de uso):
```
hardware:raspberry-pi | hardware:laptop-friendly | hardware:server-grade | 
hardware:cloud-only | hardware:edge-device
```

---

### 5E) Modalidades IA

**Qué tipos de IA soporta** (sin distinguir input/output):

```
ai:text (procesa/genera texto) |
ai:code (procesa/genera código) |
ai:image (procesa/genera imágenes) |
ai:audio (procesa/genera audio, STT, TTS, análisis) |
ai:video (procesa/genera vídeo) |
ai:vision (entiende imágenes, análisis visual) |
ai:multimodal (múltiples modalidades combinadas) |
ai:tts (text-to-speech específicamente) |
ai:stt (speech-to-text) |
ai:music (generación de música) |
ai:spanish (soporta español) |
ai:multilingual (múltiples idiomas)
```

---

## TIER 6: PATRONES DE INTEGRACIÓN

**Pregunta**: ¿Cuál es el patrón arquitectónico que usa?

**Etiquetas disponibles**:
```
pattern:abstraction-layer | pattern:translator-pattern | pattern:orchestration-hub | 
pattern:approval-loop | pattern:guard-rails | pattern:behavioral-testing | 
pattern:granular-decomposition | pattern:persistent-memory |
pattern:multi-turn-agent | pattern:autonomous-executor | pattern:legacy-bridge | pattern:loose-coupling |
pattern:real-time-collaboration | pattern:human-decision-maker |
pattern:sandboxed-execution | pattern:dependency-management | pattern:local-parity | pattern:ecosystem-embedding
```

---

## TIER 7: METODOLOGÍA/GOVERNANCE

**Pregunta**: ¿Cómo se controla y valida el sistema? ¿Quién decide?

**Etiquetas disponibles**:
```
CONTROL:
governance:human-in-the-loop | governance:human-approval-required | governance:ai-as-tactical-tool | 
governance:human-decision-maker | governance:continuous-oversight | governance:implicit-trust | 
governance:domain-expertise-required

VALIDACIÓN:
validation:characterizing-tests-first | validation:continuous-validation | validation:automated-regression-detection | 
validation:incremental-rollout | validation:behavioral-testing

DOCUMENTACIÓN:
docs:persistent-documentation | docs:explicit-boundaries | docs:critical-path-identification

RESPONSABILIDAD:
responsibility:ai-as-executor | responsibility:human-retains-decision | responsibility:reversible-actions
```

---

## TIER 8: SECURITY/RISK PROFILE

**Pregunta**: ¿Cómo se defiende? ¿Cuál es el riesgo?

**Etiquetas disponibles**:
```
DEFENSA:
defense:methodological-defense | defense:sandbox-defense | defense:human-oversight | defense:hybrid

CONFIANZA:
trust:capability-trust-low | trust:capability-trust-high | trust:sandbox-trust-medium | trust:sandbox-trust-critical

SUPERFICIE DE RIESGO:
risk-surface:code-execution | risk-surface:unrestricted-bash | risk-surface:permission-surface-broad | 
risk-surface:permission-surface-narrow | risk-surface:file-system-access | risk-surface:network-access | 
risk-surface:credentials-storage | risk-surface:data-exposure

MODO DE FALLO:
failure:operator-error | failure:sandbox-escape | failure:logic-break | failure:single-point-of-failure

MITIGACIÓN:
mitigation:explicit-boundaries | mitigation:approval-required | mitigation:visibility | mitigation:vague-salvaguards

TRANSPARENCIA:
transparency:acknowledges-risk | transparency:risk-detailed | transparency:risk-vague
```

---

## TIER 9: STRATEGIC POSITIONING & ECOSYSTEM

**Pregunta**: ¿Cuál es la estrategia empresarial?

**Etiquetas disponibles**:
```
INTENCIÓN:
strategy:safety-focused | strategy:capability-focused | strategy:ecosystem-hub | 
strategy:democratization | strategy:hybrid

POSICIONAMIENTO:
positioning:vs-ide-tools | positioning:vs-rpa-platforms | positioning:vs-automation-platforms | 
positioning:vs-competitors-direct | positioning:alternative-to-proprietary

LOCK-IN:
lock-in:none | lock-in:implicit-capability | lock-in:explicit-integration | lock-in:ecosystem-dependent

CONSOLIDACIÓN:
consolidation:hub-positioning | consolidation:ecosystem-embedding | consolidation:platform-ambition

VENDOR RISK:
vendor-risk:single-point-of-failure | vendor-risk:permission-concentration | 
vendor-risk:data-exposure-centralization | vendor-risk:switching-cost-increase

FILOSOFÍA:
philosophy:humans-decide | philosophy:ai-can-do | philosophy:ai-executes-what-approved
```

---

## CLUSTERS SUGERIDOS

**Después de clasificar, revisa si hay patrones Tier 3 que combinen:**

**CLUSTER A: "Brecha promesa-realidad"**
```
gap-documentation + community-discovery + [risk-mitigation O quality-assurance-failure]
→ Relevancia: Entender qué promete vs qué entrega (evaluación de confianza)
```

**CLUSTER B: "Herramientas que puedes construir hoy"**
```
novel-integration + multi-turn-agent + deployment:local + [pattern:X]
→ Relevancia: ACTIONABLE (puedo implementar esto)
```

**CLUSTER C: "Production-safe automation"**
```
human-in-the-loop + guard-rails + behavioral-testing + risk-mitigation + continuous-validation
→ Relevancia: ENTERPRISE (mission-critical, safe)
```

**CLUSTER D: "Platform consolidation"**
```
ecosystem-hub-positioning + lock-in:explicit + multi-platform-orchestration
→ Relevancia: Strategic arms race visible
```

**CLUSTER E: "Democratización con potencial"**
```
democratization + open-source + capability-expansion
→ Relevancia: Oportunidades de negocio/productos
```

---

## SCORING

**Basado en clusters de Tier 3:**

- **BAJO (30-50)**: Un solo tag Tier 3, sin clusters claros, o crítica de fallo
- **MEDIO (50-75)**: 2-3 tags Tier 3, algo de patrón pero incompleto
- **ALTO (75-95)**: 3+ tags Tier 3 + cluster claro + implementación (Tier 5) + governance (Tier 7)


---
## SALIDA

Devuelve un **array JSON** con la siguiente estructura:

```json
[
  {
    "post_id": "reddit_abc123",
    "tier_tags": {
      "tier1": ["claude", "anthropic"],
      "tier2": ["data-retrieval", "nlp-integration"],
      "tier3": ["capability-expansion", "transparency-in-action", "community-discovery", "democratization"],
      "tier4": ["trust-deficit", "business-model-shift"],
      "tier5": ["tool:claude-opus-4.5", "language:python", "os:web-only", "server:api-rest", "cpu:standard", "memory:standard", "gpu:none", "ai:text", "ai:multilingual"],
      "tier6": ["pattern:abstraction-layer", "pattern:translator-pattern"],
      "tier7": ["governance:human-decision-maker", "docs:explicit-boundaries", "responsibility:human-retains-decision"],
      "tier8": ["defense:methodological-defense", "trust:capability-trust-high", "risk-surface:data-exposure", "transparency:acknowledges-risk"],
      "tier9": ["strategy:safety-focused", "positioning:vs-proprietary", "philosophy:humans-decide"]
    },
    "clusters": ["CLUSTER A: brecha-promesa-realidad (transparency-in-action + capability-expansion + methodological-defense)", "CLUSTER E: democratización-con-potencial (democratization + transparency + trust-building)"],
    "scoring": 72
  },
  {
    "post_id": "reddit_xyz789",
    "tier_tags": {
      "tier1": ["openai", "chatgpt"],
      "tier2": ["code-generation"],
      "tier3": ["engagement-bait"],
      "tier4": [],
      "tier5": ["tool:chatgpt", "language:python", "os:web-only", "server:api-rest", "ai:text"],
      "tier6": [],
      "tier7": [],
      "tier8": [],
      "tier9": []
    },
    "clusters": [],
    "scoring": 35
  }
]
```

**NOTAS FINALES**:
- **NO uses backticks** en tu respuesta
- **Si no aplica un Tier, déjalo vacío []**
- **Usa nuevas etiquetas** solo si es necesario
- **Consistency**: todos los tags en `lowercase-con-guiones`
- **Un objeto por cada post_id** proporcionado

Clasifica ahora todos los posts en el array JSON.

---
