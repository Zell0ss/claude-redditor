# ClaudeRedditor - Sistema de Tagging por Tier

> **Propósito**: Clasificar nuevos artículos de forma consistente, evitando sinónimos y manteniendo coherencia terminológica.
>
> **Audiencia**: Claude (para clasificación) y Josem (para revisión)
>
> **Uso**: Aplicar cada pregunta en orden. Responder con etiquetas de la lista sugerida o dejar vacío si no aplica.

---

## TIER 1: IDENTIFICADORES

**Pregunta**: ¿Qué entidades específicas (empresas, productos, protocolos) son el sujeto principal?

**Instrucción**: Selecciona EXACTAMENTE aquellas que son protagonistas. No incluyas referencias casuales.

**Etiquetas disponibles**:
```
EMPRESAS/PROYECTOS:
- anthropic
- openai
- cloudflare
- ai2
- google
- meta
- deepmind
- microsoft

PRODUCTOS/MODELOS:
- claude
- claude-code
- chatgpt
- gemini
- gpt-4
- llama

PLATAFORMAS/INFRAESTRUCTURA:
- cloudflare-workers
- matrix-protocol
- zork
- slack
- figma
- asana
- github

FORMATO:
(Ej: cloudflare, matrix-protocol, claude)
```

**Nota**: Si aparece una empresa/producto NO en la lista, propón uno nuevo explícitamente: `[NEW: nombre-producto]`

---

## TIER 2: CATEGORÍA TÉCNICA

**Pregunta**: ¿En qué dominio técnico/funcional se inscribe el artículo?

**Instrucción**: Elige 1-2 máximo. Es el "QUÉ HACE" (no por qué).

**Etiquetas disponibles**:
```
EJECUCIÓN:
- code-generation
- code-execution
- code-quality
- refactoring
- testing
- debugging

INFRAESTRUCTURA:
- infrastructure
- cloud-native
- containerization
- package-management
- api-integration

INTELIGENCIA/CAPACIDAD:
- ai-capabilities
- nlp-integration
- reasoning
- planning
- multi-turn-planning
- autonomous-agents

INTEGRACIÓN:
- real-time-visualization
- action-execution
- multi-platform-orchestration
- workflow-automation

DOMINIO:
- interactive-fiction
- legacy-modernization
- system-access
- data-retrieval

FORMATO:
(Ej: code-generation, infrastructure)
```

---

## TIER 3: PATRÓN/SIGNAL (Lo más interesante)

**Pregunta**: ¿Cuál es el PATRÓN o HALLAZGO más interesante? ¿Qué diferencia este artículo?

**Instrucción**: Estos son los tags que crean "clusters de valor". Múltiples OK.

**Etiquetas disponibles**:
```
BRECHAS/DESALINEACIONES:
- gap-documentation (promesa ≠ realidad)
- undocumented-capabilities (hace más de lo que dice)
- emergent-behavior (capacidades inesperadas)
- quality-assurance-failure (falló QA interno)

DEMOCRATIZACIÓN:
- democratization (acceso igualitario)
- open-source (disponible en OSS)
- accessibility (interfaz natural vs sintaxis rígida)

DISCOVERY/VALIDACIÓN:
- community-discovery (encontrado por usuarios, no labs)
- user-research (data from real usage)
- capability-expansion (nuevo feature)

MEJORA DE EXPERIENCIA:
- friction-elimination (tab-switching → integrated)
- developer-experience-improvement
- user-experience-enhancement

TRANSPARENCIA:
- transparency-in-action (usuario ve qué hace la IA)
- explainability (reasoning visible)

METODOLOGÍA:
- human-in-the-loop (humano toma decisiones)
- methodology-over-speed (rigor > velocidad)
- methodology-first (framework antes de ejecución)

COMPETICIÓN:
- competitive-differentiation
- vendor-feature-arms-race
- competitive-landscape

SEGURIDAD/CONFIANZA:
- risk-mitigation (activamente mitigado)
- safety-validation (nuevo problema de seguridad)
- safety-concerns (flags de seguridad)

OTROS:
- novel-integration (combinación creativa)
- legacy-bridge (conecta viejo + nuevo)

FORMATO:
(Ej: gap-documentation, community-discovery, human-in-the-loop)
```

**REGLA IMPORTANTE**: Si el artículo menciona múltiples patrones, incluye todos. Este Tier genera los "clusters valiosos".

---

## TIER 4: IMPLICACIÓN

**Pregunta**: ¿Cuál es el impacto o significado más amplio?

**Instrucción**: Conecta el patrón (Tier 3) con sus consecuencias. 1-2 máximo.

**Etiquetas disponibles**:
```
CONFIANZA:
- trust-deficit (impacta reputación negativa)
- vendor-credibility (qué tan confiable es el vendor)

CAPACIDAD:
- legacy-modernization-viable (ahora es posible)
- business-model-shift (de X a Y)

SEGURIDAD:
- safety-alignment (capacidades no totalmente caracterizadas)

ARQUITECTURA:
- characterization-gap (no sabemos todos los límites)
- integration-depth-increasing (más tightly coupled)

MERCADO:
- economic-value (ahorro de tiempo/costo)
- market-positioning (vs competencia)
- lock-in-strategy (aumenta switching cost)

FORMATO:
(Ej: trust-deficit, legacy-modernization-viable)
```

---

## TIER 5: IMPLEMENTACIÓN/STACK

**Pregunta**: ¿Con QUÉ tecnologías específicas se implementa?

**Instrucción**: Muy granular. Documenta lo concreto para "qué puedo construir/usar".

**Etiquetas disponibles**:
```
HERRAMIENTAS:
- tool:claude-code
- tool:chatgpt-containers
- tool:tambo
- tool:[NEW: nombre-específico]

LENGUAJES:
- language:python
- language:typescript
- language:rust
- language:go
- language:javascript
- language:bash

FRAMEWORKS:
- framework:django
- framework:fastapi
- framework:[NEW: nombre]

INTEGRACIONES ESPECÍFICAS:
- integration:slack
- integration:figma
- integration:asana
- integration:amplitude
- integration:box
- integration:canva
- integration:clay
- integration:hex
- integration:monday
- integration:[NEW: nombre]

DEPLOYMENT:
- deployment:cloud-hosted
- deployment:production
- deployment:self-hosted
- deployment:client-side
- deployment:edge-compatible
- deployment:api-service

ARQUITECTURA:
- architecture:monolith
- architecture:microservices
- architecture:serverless
- architecture:distributed
- architecture:decentralized

CAPABILITY ESPECÍFICA:
- capability:bash-execution
- capability:pip-install
- capability:npm-install
- capability:file-download
- capability:code-execution
- capability:reasoning
- capability:planning
- capability:tool-use
- capability:mcp-integration
- capability:real-time-viz

SCOPE/ESCALA:
- scope:local-execution
- scope:cloud-dependent

FORMATO:
(Ej: tool:claude-code, language:python, deployment:production)
```

**Nota**: Estos tags son los más "nuevos" que pueden variar por artículo. No dudes en proponer `[NEW: ...]`

---

## TIER 6: PATRONES DE INTEGRACIÓN

**Pregunta**: ¿Cuál es el PATRÓN arquitectónico o de integración que usa?

**Instrucción**: Describe HOW (no WHAT ni WHY). Múltiples OK si son patrones distintos.

**Etiquetas disponibles**:
```
PATRÓN EJECUTIVO:
- pattern:abstraction-layer (IA intermedia entre usuario y sistema)
- pattern:translator-pattern (NL → sintaxis restrictiva)
- pattern:orchestration-hub (coordina múltiples plataformas)
- pattern:approval-loop (humano valida antes de ejecutar)
- pattern:guard-rails (límites explícitos sobre qué NO hacer)
- pattern:behavioral-testing (captura comportamiento actual)
- pattern:granular-decomposition (tasks muy específicas)
- pattern:persistent-memory (documentación que persiste)

PATRÓN AUTÓNOMO:
- pattern:multi-turn-agent (mantiene coherencia sobre N acciones)
- pattern:autonomous-executor (ejecuta sin intervención)
- pattern:legacy-bridge (conecta viejo sistema con nuevo)
- pattern:loose-coupling (IA es wrapper, no embebida)

PATRÓN COLABORATIVO:
- pattern:real-time-collaboration (usuario + AI iterando)
- pattern:human-decision-maker (humano elige dirección)

PATRÓN TÉCNICO:
- pattern:sandboxed-execution (aislamiento técnico)
- pattern:dependency-management (maneja librerías/paquetes)
- pattern:local-parity (imita experiencia dev local)
- pattern:ecosystem-embedding (tightly integrated a suite)

FORMATO:
(Ej: pattern:abstraction-layer, pattern:approval-loop, pattern:multi-turn-agent)
```

---

## TIER 7: METODOLOGÍA/GOVERNANCE

**Pregunta**: ¿Cómo se CONTROLA y VALIDA el sistema? ¿Quién decide qué pasa?

**Instrucción**: Define el MODELO DE CONFIANZA. Describe filosofía, no ejecución.

**Etiquetas disponibles**:
```
CONTROL DE EJECUCIÓN:
- governance:human-in-the-loop (humano toma decisiones)
- governance:human-approval-required (approval gates explícitos)
- governance:ai-as-tactical-tool (IA no tiene estrategia)
- governance:human-decision-maker (humano elige dirección)
- governance:continuous-oversight (monitoreo activo)
- governance:implicit-trust (usuario confía IA hará bien)
- governance:domain-expertise-required (necesita entender el dominio)

VALIDACIÓN:
- validation:characterizing-tests-first (captura antes de cambiar)
- validation:continuous-validation (test after each)
- validation:automated-regression-detection
- validation:incremental-rollout (no big-bang)
- validation:behavioral-testing

DOCUMENTACIÓN:
- docs:persistent-documentation (vive en repo/repo)
- docs:explicit-boundaries (qué no tocar está documentado)
- docs:critical-path-identification (sabe dónde están los riesgos)

RESPONSABILIDAD:
- responsibility:ai-as-executor (IA hace lo aprobado)
- responsibility:human-retains-decision
- responsibility:reversible-actions (se puede deshacer)

FORMATO:
(Ej: governance:human-in-the-loop, validation:characterizing-tests-first)
```

---

## TIER 8: SECURITY/RISK PROFILE

**Pregunta**: ¿Cómo se DEFIENDE el sistema? ¿Cuál es el riesgo real?

**Instrucción**: Identifica MODELO DE DEFENSA + SUPERFICIE DE RIESGO. Ej: "sandbox-only" vs "methodological".

**Etiquetas disponibles**:
```
MODELO DE DEFENSA:
- defense:methodological-defense (governance + oversight)
- defense:sandbox-defense (aislamiento técnico)
- defense:human-oversight (aprobación requerida)
- defense:hybrid (combinación de estrategias)

CONFIANZA EN COMPONENTES:
- trust:capability-trust-low (debe aprobar)
- trust:capability-trust-high (libre de ejecutar)
- trust:sandbox-trust-medium (asumido seguro)
- trust:sandbox-trust-critical (DEBE ser bulletproof)

SUPERFICIE DE RIESGO:
- risk-surface:code-execution
- risk-surface:unrestricted-bash
- risk-surface:permission-surface-broad
- risk-surface:permission-surface-narrow
- risk-surface:file-system-access
- risk-surface:network-access
- risk-surface:credentials-storage
- risk-surface:data-exposure

MODO DE FALLO:
- failure:operator-error (humano no vio la mina)
- failure:sandbox-escape (técnica falló)
- failure:logic-break (AI entendió mal)
- failure:single-point-of-failure (todo cae si falla X)

MITIGACIÓN VISIBLE:
- mitigation:explicit-boundaries (límites claros)
- mitigation:approval-required (gates)
- mitigation:visibility (usuario ve qué pasa)
- mitigation:vague-salvaguards (menciona pero no detalla)

TRANSPARENCIA DE RIESGO:
- transparency:acknowledges-risk (lo menciona)
- transparency:risk-detailed (explica riesgos)
- transparency:risk-vague (menciona pero superficial)

FORMATO:
(Ej: defense:methodological-defense, risk-surface:code-execution, mitigation:explicit-boundaries)
```

---

## TIER 9: STRATEGIC POSITIONING & ECOSYSTEM

**Pregunta**: ¿CUÁL ES LA ESTRATEGIA EMPRESARIAL detrás? ¿Por qué lo hace así?

**Instrucción**: Visión de negocio + posicionamiento competitivo. Define la INTENCIÓN.

**Etiquetas disponibles**:
```
INTENCIÓN ESTRATÉGICA:
- strategy:safety-focused (minimizar riesgo)
- strategy:capability-focused (maximizar freedom)
- strategy:ecosystem-hub (ser centro de plataforma)
- strategy:democratization (acceso abierto)
- strategy:hybrid (múltiples objetivos)

POSICIONAMIENTO:
- positioning:vs-ide-tools (compite con IDEs)
- positioning:vs-rpa-platforms (compite con UiPath/Blue Prism)
- positioning:vs-automation-platforms (compite con Zapier)
- positioning:vs-competitors-direct (OpenAI vs Anthropic)
- positioning:alternative-to-proprietary

MECANISMO DE LOCK-IN:
- lock-in:none (usuario libre de marcharse)
- lock-in:implicit-capability (sandboxed features)
- lock-in:explicit-integration (9+ integraciones)
- lock-in:ecosystem-dependent

CONSOLIDACIÓN:
- consolidation:hub-positioning (centro de trabajo)
- consolidation:ecosystem-embedding (tightly coupled)
- consolidation:platform-ambition (no solo chatbot)

RIESGO DE VENDOR:
- vendor-risk:single-point-of-failure (todo falla si cae X)
- vendor-risk:permission-concentration (un vendor ve todo)
- vendor-risk:data-exposure-centralization (datos en un lugar)
- vendor-risk:switching-cost-increase

MARKET TIMING:
- market:targets-enterprise
- market:targets-knowledge-workers
- market:targets-remote-teams
- market:competitive-arms-race

FILOSOFÍA OPERACIONAL:
- philosophy:humans-decide (usuario manda)
- philosophy:ai-can-do (IA tiene libertad)
- philosophy:ai-executes-what-approved (IA + humano)

FORMATO:
(Ej: strategy:ecosystem-hub, lock-in:explicit-integration, vendor-risk:data-exposure-centralization)
```

---

## RESUMEN: ORDEN DE APLICACIÓN

Cuando clasifiques un artículo NUEVO, sigue este orden:

1. **TIER 1** → ¿Qué entidades son protagonistas?
2. **TIER 2** → ¿En qué dominio técnico opera?
3. **TIER 3** → ¿Cuál es el patrón/signal interesante? ⭐ (MÁS IMPORTANTE)
4. **TIER 4** → ¿Cuál es la implicación?
5. **TIER 5** → ¿Con qué tech se implementa? (si aplica)
6. **TIER 6** → ¿Qué patrón arquitectónico usa? (si aplica)
7. **TIER 7** → ¿Cómo se controla? (si aplica)
8. **TIER 8** → ¿Cuál es el perfil de riesgo? (si aplica)
9. **TIER 9** → ¿Cuál es la estrategia? (si aplica)

**Regla de oro**: Un artículo puede ser VACÍO en Tier 5-9. Eso está bien. Lo importante es Tier 1-4.

---

## NOTAS FINALES

**1. Consistencia**: Todas las etiquetas están escritas en `lowercase-con-guiones`. NO uses variantes (ej: no mezcles `human-in-the-loop` con `human_in_loop`).

**3. Clustering automático**: Con este sistema, artículos con Tier 3 similar crearán automáticamente clusters:
   - `gap-documentation` + `community-discovery` = "Brecha promesa-realidad"
   - `human-in-the-loop` + `guard-rails` + `methodology-first` = "Production-safe automation"
   - `ecosystem-hub` + `lock-in:explicit` = "Platform consolidation"
   - capability-expansion + friction-elimination = "Herramientas que puedes construir hoy"
   - risk-surface:unrestricted-bash + transparency:risk-vague = "Riesgo de seguridad con defensa unclear"

**4. Scoring**: Los puntos bonus en ClaudeRedditor pueden mapearse así:
   ```python
   HIGH_VALUE = clusters de Tier 3 que combinen patrones interesantes
   ENTERPRISE_VALUE = Tier 7 + Tier 8 (governance + risk management)
   ACTIONABLE = Tier 5 + Tier 6 (tech + arquitectura)
   STRATEGIC = Tier 9 (quién compite con quién)
   ```

**5. Para el podcast**: Tier 9 es lo que genera narrativa. Usa eso para "La paradoja de la confianza".