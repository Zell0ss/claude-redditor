
# PROMPT: Clasificar artículos de vinos

## INSTRUCCIÓN GENERAL

Clasifica el siguiente artículo en 8 Tiers + scoring.
Responde en el formato indicado abajo.

---

## FORMATO DE RESPUESTA
Devuelve un json con una clave por cada tier y la lista de etiquetas de cada uno, scoring y clusters
No uses backticks para poder convertirlo a diccionario en python directamente.
No añadas mas campos que estos al json.
A ser posible usa las etiquetas de la lista sugerida para cada tier, pero si es absolutamente necesario puedes crear nuevas si ninguna de las existentes se ajusta.

---

## TIER 1: IDENTIFICADORES

**Pregunta**: ¿Qué vinos/productores/regiones son el sujeto principal?

**Etiquetas disponibles**:
```
[PRODUCTOR]: saalwachter | josh | apothic | caymus | meomi | [NEW: nombre-si-no-existe]

[REGIÓN]: liguria | alemania | california | italia | españa | francia | portugal | [NEW: nombre-si-no-existe]

[VARIETAL]: silvaner | cabernet-sauvignon | pinot-noir | riesling | chardonnay | sauvignon-blanc | merlot | syrah | tempranillo | [NEW: nombre-si-no-existe]

[TIPO]: vino-blanco | vino-tinto | vino-rosado | vino-espumoso | vino-dulce | vino-fortificado | vino-natural | vino-biodinamico | vino-orange

[ESTILO]: old-world | new-world | natural-wine | low-intervention | high-alcohol | low-alcohol
```

---

## TIER 2: GÉNERO/FORMATO DEL POST

**Pregunta**: ¿Qué tipo de contenido es?

**Instrucción**: Elige exactamente 1.

**Etiquetas disponibles**:
```
formato:tasting-note | formato:deep-dive-tecnico | formato:solicitud-consejo |
formato:educacion-explainer | formato:historia-contexto | formato:maridaje-pairing |
formato:negocio-operaciones | formato:opinion-debate
```

---

## TIER 3: PATRÓN/HALLAZGO PRINCIPAL

**Pregunta**: ¿Cuál es el patrón o hallazgo más interesante?

**Instrucción**: Múltiples OK. Estos tags generan "clusters de valor".

**Etiquetas disponibles**:
```
CALIDAD & COHERENCIA:
quality-gap | value-proposition | price-vs-reality | overrated | underrated | 
hidden-gem | consistency-issue | quality-assurance-failure

SENSORIALES:
mineral-complexity | fruit-forward | aromatic-intensity | texture-mouthfeel | 
freshness-acidity | tannin-structure | aging-potential

TÉCNICA & PROCESO:
process-innovation | fermentation-style | oak-influence | natural-wine-techniques |
residual-sugar-confusion | transparency-gap

CONSUMER INSIGHTS:
consumer-deception-potential | accessibility-paradox | palate-education | 
bridge-wine | gateway-wine | polarizing-profile

DESCUBRIMIENTO:
community-discovery | producer-spotlight | emerging-region | forgotten-varietal |
new-technique-adoption

NEGOCIO & OPERACIONES:
sourcing-strategy | pricing-strategy | market-positioning | distribution-challenge |
supply-chain-insight | operator-practical-question
```

---

## TIER 4: IMPLICACIÓN / SIGNIFICADO AMPLIO

**Pregunta**: ¿Cuál es el impacto o significado más amplio?

**Instrucción**: 1-2 máximo.

**Etiquetas disponibles**:
```
CONFIANZA & CREDIBILIDAD:
trust-deficit | transparency-needed | industry-accountability | misleading-marketing

EDUCACIÓN & ACCESO:
democratization-of-knowledge | palate-development | technical-literacy |
demystification | accessibility-improvement

ECONOMÍA:
business-model-sustainability | pricing-psychology | value-perception |
market-consolidation | small-producer-viability

INDUSTRIA:
industry-shift | regulatory-gap | best-practice-emerging | standardization-needed
```

---

## TIER 5: CARACTERIZACIÓN SENSORIAL & TÉCNICA

### 5A) Perfil sensorial descrito

**taste:X** (notas de sabor):
```
taste:mineral | taste:frutal | taste:floral | taste:herbaceo | taste:especiado |
taste:terroso | taste:mantecoso | taste:acaramelado | taste:citrico | taste:tropical |
taste:frutos-rojos | taste:frutos-negros | taste:confitado
```

**texture:X** (estructura en boca):
```
texture:sedoso | texture:cremoso | texture:tannico | texture:fresco | texture:jugoso |
texture:ácido | texture:alcohólico | texture:robusto | texture:elegante | texture:ligero
```

**aroma:X** (intensidad aromática):
```
aroma:delicado | aroma:moderado | aroma:intenso | aroma:complejo
```

---

### 5B) Datos técnicos (si aplica)

**alcohol:X**:
```
alcohol:bajo | alcohol:moderado | alcohol:alto | alcohol:very-high
```

**residual-sugar:X**:
```
residual-sugar:seco | residual-sugar:off-dry | residual-sugar:semi-dulce | residual-sugar:dulce
```

**age:X**:
```
age:joven | age:crianza | age:reserva | age:gran-reserva | age:vintage-[YEAR]
```

**elevage:X** (tiempo en barrica/botella):
```
elevage:none | elevage:stainless-steel | elevage:neutral-oak | elevage:french-oak | elevage:american-oak | elevage:extended-bottle-age
```

---

### 5C) Proceso & método

**production:X**:
```
production:conventional | production:natural-wine | production:orange-wine |
production:low-intervention | production:biodynamic | production:organic |
production:vegan | production:skin-contact
```

---

## TIER 6: CONTEXTO DE CONSUMO & MARIDAJE

**Pregunta**: ¿Cuándo, dónde y con qué se bebe?

**Instrucción**: Múltiples OK.

**Etiquetas disponibles**:
```
MOMENTO:
occasion:aperitif | occasion:lunch | occasion:dinner | occasion:casual-drinking |
occasion:celebration | occasion:contemplation | occasion:food-pairing | occasion:session-drinking

ENTORNO:
setting:terrace | setting:restaurant | setting:casual | setting:formal | setting:wine-bar |
setting:natural-outdoor | setting:cellar

MARIDAJE:
pairing:seafood | pairing:light-dishes | pairing:cheese | pairing:meat | pairing:spicy |
pairing:vegetarian | pairing:dessert | pairing:aperitif-food | pairing:versatile-pairing

PÚBLICO:
audience:beginner-palate | audience:wine-enthusiast | audience:sommelier | audience:operator |
audience:casual-drinker | audience:collector
```

---

## TIER 7: EVALUACIÓN & POSICIONAMIENTO

**Pregunta**: ¿Cómo evalúas este vino? ¿Cuál es su posición?

**Instrucción**: 1-2 máximo.

**Etiquetas disponibles**:
```
EVALUACIÓN CUALITATIVA:
evaluation:excellent-coherence | evaluation:good-value | evaluation:overpriced |
evaluation:underpriced | evaluation:polarizing | evaluation:accessible | evaluation:complex |
evaluation:drinkable-now | evaluation:age-worthy | evaluation:requires-education

POSICIONAMIENTO COMERCIAL:
positioning:entry-level | positioning:mid-range | positioning:premium | positioning:luxury |
positioning:cult-wine | positioning:mass-market | positioning:niche | positioning:emerging

RIESGO & CONSIDERACIONES:
risk:requires-decanting | risk:needs-aeration | risk:short-drinking-window | risk:brokers-heavily |
risk:supply-inconsistent | risk:producer-inconsistent
```

---

## TIER 8: ESTRATEGIA EDITORIAL & INTENCIÓN

**Pregunta**: ¿Cuál es tu intención al publicar esto?

**Etiquetas disponibles**:
```
INTENCIÓN:
strategy:education-focused | strategy:discovery-driven | strategy:critical-analysis |
strategy:practical-advice | strategy:community-engagement | strategy:documentation |
strategy:debate-provocation | strategy:operator-support

NIVEL DE PROFUNDIDAD:
depth:surface-appreciation | depth:technical-analysis | depth:consumer-investigation |
depth:industry-insider | depth:research-based

TONO:
tone:enthusiastic | tone:analytical | tone:critical | tone:conversational |
tone:investigative | tone:practical | tone:educational
```

---

## CLUSTERS SUGERIDOS

**Después de clasificar, revisa si hay patrones Tier 3 que combinen:**

**CLUSTER A: "Brecha productor-mercado"**
```
quality-gap + transparency-gap + consumer-deception-potential
→ Relevancia: El vino promete X pero entrega Y; el mercado no lo sabe
```

**CLUSTER B: "Vino puente/transición"**
```
bridge-wine + accessibility-paradox + palate-education
→ Relevancia: ACTIONABLE (recomendable para desarrollar paladar)
```

**CLUSTER C: "Deep-dive técnico"**
```
process-innovation + residual-sugar-confusion + transparency-gap
→ Relevancia: Educativo (explica algo que la industria no comunica bien)
```

**CLUSTER D: "Gema operativa"**
```
hidden-gem + value-proposition + operator-practical-question
→ Relevancia: Útil para tomadores de decisión en hostelería/distribución
```

**CLUSTER E: "Hallazgo de descubrimiento"**
```
emerging-region + producer-spotlight + community-discovery
→ Relevancia: Oportunidad de negocio/educación al lector
```

**CLUSTER F: "Debate/investigación abierta"**
```
consumer-deception-potential + quality-assurance-failure + industry-accountability
→ Relevancia: Cuestiona estándares; genera conversación
```

---

## SCORING

**Basado en clusters de Tier 3 + complejidad de Tier 7:**

- **BAJO (20-40)**: Post simple, un solo tema, sin investigación, sin clusters claros
- **MEDIO (40-70)**: Reseña sólida con 1-2 temas, algo de patrón
- **ALTO (70-95)**: Deep-dive investigativo O reseña + análisis + patrón + implicación + cluster claro

---

## SALIDA

Devuelve un json con una clave por cada tier (tier1, tier2, tier3, tier4,...) y una lista de etiquetas, scoring y clusters.
No uses backticks para poder convertirlo a diccionario en python directamente.
No añadas mas campos que estos al json.

---

## EJEMPLO DE CLASIFICACIÓN REAL

Reseña Silvaner:
```
{
    "tier1": ["productor:saalwachter", "region:alemania", "varietal:silvaner", "tipo:vino-blanco", "estilo:old-world"],
    "tier2": ["formato:tasting-note"],
    "tier3": ["mineral-complexity", "quality-gap", "hidden-gem", "community-discovery"],
    "tier4": ["democratization-of-knowledge", "accessibility-improvement"],
    "tier5": ["taste:mineral", "taste:citrico", "taste:especiado", "texture:fresco", "texture:elegante", "aroma:moderado", "alcohol:moderado", "residual-sugar:seco", "production:conventional"],
    "tier6": ["occasion:aperitif", "occasion:lunch", "setting:terrace", "pairing:seafood", "pairing:light-dishes", "audience:wine-enthusiast"],
    "tier7": ["evaluation:excellent-coherence", "evaluation:good-value", "positioning:mid-range", "evaluation:drinkable-now"],
    "tier8": ["strategy:discovery-driven", "depth:technical-analysis", "tone:enthusiastic"],
    "clusters": ["CLUSTER A: brecha-productor-mercado (mineral-complexity + quality-gap + hidden-gem)", "CLUSTER B: vino-puente (accessibility-paradox + palate-education)"],
    "scoring": 68
}
```

Josh Cabernet (investigación):
```
{
    "tier1": ["productor:josh", "region:california", "varietal:cabernet-sauvignon", "tipo:vino-tinto", "estilo:new-world"],
    "tier2": ["formato:deep-dive-tecnico"],
    "tier3": ["quality-gap", "transparency-gap", "residual-sugar-confusion", "consumer-deception-potential", "price-vs-reality"],
    "tier4": ["trust-deficit", "transparency-needed", "industry-accountability"],
    "tier5": ["taste:frutal", "texture:tannico", "aroma:intenso", "alcohol:alto", "residual-sugar:seco", "production:conventional"],
    "tier6": ["pairing:meat", "audience:casual-drinker"],
    "tier7": ["evaluation:polarizing", "positioning:mass-market", "evaluation:accessible"],
    "tier8": ["strategy:critical-analysis", "strategy:consumer-investigation", "depth:consumer-investigation", "tone:investigative"],
    "clusters": ["CLUSTER C: deep-dive-tecnico (transparency-gap + residual-sugar-confusion + industry-accountability)", "CLUSTER F: debate-investigacion-abierta (consumer-deception-potential + quality-assurance-failure)"],
    "scoring": 82
}
```

Wine List (operaciones):
```
{
    "tier1": ["region:liguria", "tipo:vino-blanco", "tipo:vino-tinto", "tipo:vino-rosado"],
    "tier2": ["formato:solicitud-consejo"],
    "tier3": ["sourcing-strategy", "pricing-strategy", "operator-practical-question", "market-positioning"],
    "tier4": ["business-model-sustainability", "industry-shift"],
    "tier5": [],
    "tier6": ["occasion:lunch", "occasion:aperitif", "setting:terrace", "setting:restaurant", "audience:operator"],
    "tier7": ["positioning:entry-level", "positioning:mid-range", "positioning:premium"],
    "tier8": ["strategy:operator-support", "strategy:practical-advice", "depth:industry-insider", "tone:conversational"],
    "clusters": ["CLUSTER D: gema-operativa (operator-practical-question + sourcing-strategy + pricing-strategy)"],
    "scoring": 55
}
```

---

## NOTAS IMPORTANTES
- **No uses backticks para poder convertirlo a diccionario en python directamente**
- **Si no aplica un Tier, déjalo vacío []**: no fuerces etiquetas
- **Propón nuevas etiquetas** si encuentras algo no cubierto
- **Consistency**: todos los tags en `lowercase-con-guiones`
- **Tier 1** siempre debe tener al menos `tipo:` y `estilo:` si es un vino específico. Si es operacional/abstracto, puede estar vacío
- **Tier 2** siempre debe tener EXACTAMENTE 1 etiqueta de formato
```

---
