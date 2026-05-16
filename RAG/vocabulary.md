# DARW Vocabulary

Schema version: `darw-vocabulary-v1`

This file is the **script-readable ontology cache**.
It is the authority for all `canonical_id` values used in `edges` fields.
Do not hardcode physics terms in scripts.

---

## Namespaces

| Namespace | Meaning |
|---|---|
| `physh:` | Term from APS PhySH controlled vocabulary |
| `local:` | Project-local controlled term |
| `alias:` | Non-canonical alias — never written as a final `canonical_id` |

---

## Categories

| Category | Description |
|---|---|
| `research_areas` | Sub-field or research program |
| `physical_systems` | Detector, material, or physical system |
| `techniques` | Experimental or computational methods |
| `properties` | Physical observables or quantities |
| `models` | Theoretical models or frameworks |
| `observables` | Measured quantities |
| `datasets` | Named datasets or data releases |
| `experiments` | Named experiments or facilities |

---

## Terms

```yaml
terms:
- canonical_id: physh:d9e32a6d-d42e-430a-9665-10aaf0776e26
  label: Nuclear reactors
  namespace: physh
  category: research_areas
  aliases: []
  parent: null
  related: []
  source: physh
  needs_review: false
- canonical_id: physh:db3d74af-cef8-4eeb-a6da-910a42929da6
  label: Neutrinos
  namespace: physh
  category: physical_systems
  aliases: []
  parent: null
  related: []
  source: physh
  needs_review: false
- canonical_id: physh:8568a1b2-908f-465b-9013-9f8ec543070c
  label: Magnetic moment
  namespace: physh
  category: properties
  aliases: []
  parent: null
  related: []
  source: physh
  needs_review: false
- canonical_id: physh:4df8c87e-3d2c-4f9b-a45e-09913597d30e
  label: Cooper pairs
  namespace: physh
  category: research_areas
  aliases: []
  parent: null
  related: []
  source: physh
  needs_review: false
- canonical_id: physh:38e21fa2-d4a0-4206-a623-ab3eb9ba82a8
  label: Noise
  namespace: physh
  category: research_areas
  aliases: []
  parent: null
  related: []
  source: physh
  needs_review: false
- canonical_id: physh:024cf552-b967-4a51-8b54-d209e10f0bc7
  label: Dark matter
  namespace: physh
  category: research_areas
  aliases: []
  parent: null
  related: []
  source: physh
  needs_review: false
- canonical_id: physh:4501b22f-36e3-4024-8fe8-7222b02313eb
  label: Solar neutrinos
  namespace: physh
  category: research_areas
  aliases: []
  parent: null
  related: []
  source: physh
  needs_review: false
- canonical_id: local:coherent-elastic-neutrino-nucleus-scattering
  label: coherent elastic neutrino-nucleus scattering
  namespace: local
  category: research_areas
  aliases: []
  parent: null
  related: []
  source: script
  needs_review: true
- canonical_id: local:liquid-xenon
  label: liquid xenon
  namespace: local
  category: physical_systems
  aliases: []
  parent: null
  related: []
  source: script
  needs_review: true
- canonical_id: local:ghz-resonator
  label: GHz resonator
  namespace: local
  category: physical_systems
  aliases: []
  parent: null
  related: []
  source: script
  needs_review: true
- canonical_id: local:electron-lifetime
  label: electron lifetime
  namespace: local
  category: properties
  aliases: []
  parent: null
  related: []
  source: script
  needs_review: true
- canonical_id: local:electric-field
  label: electric field
  namespace: local
  category: properties
  aliases: []
  parent: null
  related: []
  source: script
  needs_review: true
- canonical_id: local:purification-efficiency
  label: purification efficiency
  namespace: local
  category: properties
  aliases: []
  parent: null
  related: []
  source: script
  needs_review: true
- canonical_id: local:energy-threshold
  label: energy threshold
  namespace: local
  category: properties
  aliases: []
  parent: null
  related: []
  source: script
  needs_review: true
- canonical_id: local:outgassing-rate
  label: outgassing rate
  namespace: local
  category: observables
  aliases: []
  parent: null
  related: []
  source: script
  needs_review: true
- canonical_id: local:flow-rate
  label: flow rate
  namespace: local
  category: observables
  aliases: []
  parent: null
  related: []
  source: script
  needs_review: true
- canonical_id: local:nuclear-recoil
  label: nuclear recoil
  namespace: local
  category: observables
  aliases: []
  parent: null
  related: []
  source: script
  needs_review: true
- canonical_id: local:nucleus
  label: NUCLEUS
  namespace: local
  category: experiments
  aliases: []
  parent: null
  related: []
  source: script
  needs_review: true
- canonical_id: local:conus
  label: CONUS
  namespace: local
  category: experiments
  aliases: []
  parent: null
  related: []
  source: script
  needs_review: true
```

---

## Rules

1. `edges` may only contain `canonical_id` values from this file.
2. Unknown terms enter `local:` with `needs_review: true`.
3. Aliases are for matching only — never written as final edge values.
4. APS PhySH API may be used for lookup; this cache is the authoritative fallback.
5. Conflicting terms must not be auto-merged.
6. `uncategorized` is temporary — propose a diff before committing new terms.

---

## Adding a new term

```yaml
- canonical_id: "local:new-term-key"
  label: "Human-readable label"
  namespace: "local"
  category: "research_areas"
  aliases: []
  parent: null
  related: []
  source: "llm"                   # physh | llm | user | script
  needs_review: true
```
