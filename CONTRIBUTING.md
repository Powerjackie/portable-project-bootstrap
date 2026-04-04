# Contributing

Thanks for your interest in improving Portable Project Bootstrap.

## Before You Change Anything

1. Read `README.md`.
2. Read `docs/workspace-suite-overview.md`.
3. Keep the suite boundaries intact:
   - validator checks readiness
   - router resolves existing-project entry
   - bootstrap handles brand-new initialization
   - the planner decides what to do
   - the executor decides how to apply the planned actions

## Development Guidelines

- keep fail-closed behavior intact
- do not silently fall back from `new` to `legacy`
- do not auto-apply manual patch output
- do not turn validator or router into bootstrap variants
- keep agent-facing docs out of the repo

## Validation

Run the test suite before proposing a change:

```powershell
python -m unittest discover -s tests -v
```

If you change public docs or examples, make sure they still match the implemented behavior.
