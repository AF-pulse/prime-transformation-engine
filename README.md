# Prime Transformation Engine

Prime Transformation Engine is a ProMind Transformation Extension runtime.

It is the executable/runtime realization of ProMind Transformation Extension (PTE) concepts. It is not ProMind Core, it does not replace ProMind Core, and it must not create a parallel ProMind runtime.

ProMind Core remains the continuity substrate. The Engine must preserve Core stability and operate through additive extension architecture.

The Engine consumes PrimeMind as a governed knowledge provider. It may consume approved governed knowledge, Grounded Answer, citations, provenance, access metadata, and publication state only through authorized read-only contracts.

## Bootstrap Status

Current phase:

```text
BOOTSTRAP
```

Bootstrap permits structure and documentation only.

No runtime orchestration is implemented yet.

This repository currently contains:

- charter and alignment documentation,
- PTE taxonomy source documentation,
- ProMind extension architecture source documentation,
- an initial extension-oriented directory skeleton.

## Constraints

During bootstrap, this repository must not:

- implement transformation orchestration,
- add PrimeMind API clients,
- add credentials,
- add deployment configuration,
- modify ProMind,
- modify PrimeMind,
- modify IAM,
- create grants,
- write to Dev or Production.

## Initial Extension Structure

```text
backend/app/extensions/transformation/
  orchestration/
  pct/
  lineage/
  ctl/
  overlays/
  continuity/
  telemetry/
```

This structure mirrors the future ProMind extension integration boundary while keeping runtime behavior absent until separately authorized.
