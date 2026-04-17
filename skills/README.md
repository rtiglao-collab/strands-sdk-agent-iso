# Skills (optional)

To use AgentSkills.io-style skills with Strands, see `AgentSkills` and `Skill` in the upstream SDK (`strands.vended_plugins.skills`).

Suggested layout (example):

```text
skills/
  pdf-processing/
    SKILL.md
    ...
```

Point `AgentSkills` at these paths from `l3_runtime/agents.py` when you enable the plugin.
