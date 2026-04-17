# Memory (runtime, per user)

Default layout:

```text
memory/users/<user_key>/   # created on demand; gitignored except .gitkeep
```

Application code should only write under the active `UserScope.memory_root`. Do not store secrets here.
