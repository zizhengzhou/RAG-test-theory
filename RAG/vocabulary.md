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
terms: []
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
