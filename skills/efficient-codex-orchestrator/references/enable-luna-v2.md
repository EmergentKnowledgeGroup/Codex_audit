# Enable Luna for native multi-agent v2

Use this only when native `spawn_agent` rejects `gpt-5.6-luna` while Codex CLI
can run it. This is an advanced local catalog override, not a claim that every
Codex build or account exposes Luna. Obtain explicit user authorization before
editing global Codex configuration.

The procedure below was validated on Codex CLI 0.146.0 for Windows. Catalog
schemas can change. Codex Desktop may bundle a different runtime or consume a
different schema. Keep the custom catalog separate from `models_cache.json`
because Codex can refresh and overwrite the cache. Only the final native probe
establishes that the active Desktop runtime accepted the override.

## 1. Update and inspect Codex

```powershell
codex --version
codex debug models > $null
```

If the Windows installer accidentally resolves an MSYS/devkitPro `tar.exe`, put
`C:\Windows\System32` first in the current session's `PATH` before rerunning the
official installer.

## 2. Create a custom catalog

Read `%USERPROFILE%\.codex\models_cache.json`, clone it to a separate file such
as `%USERPROFILE%\.codex\models_catalog_custom.json`, and make these mechanical
changes in the custom copy:

1. Find the model whose `slug` is `gpt-5.6-luna`.
2. Set its `multi_agent_version` to `v2`.
3. Ensure every model object contains all fields required by the current custom
   catalog parser. On Codex 0.146.0, a cache-derived catalog required
   `supports_reasoning_summaries`; use the value reported by the current built-in
   catalog when available rather than assuming an old schema is current.

Do not rely on editing `models_cache.json` in place. It is Codex-owned and may
be refreshed. The separate custom catalog is the durable source.

## 3. Point Codex at the custom catalog

Back up `%USERPROFILE%\.codex\config.toml`, then add this top-level key:

```toml
model_catalog_json = 'C:\Users\YOUR_NAME\.codex\models_catalog_custom.json'
```

Validate before restarting:

```powershell
codex debug models > $null
```

If validation reports a missing field, do not restart into a broken catalog.
Remove or comment out `model_catalog_json` to restore the built-in catalog,
rerun `codex debug models`, compare the cache-derived objects with that output,
add the required field to every custom model object, restore the key, and rerun
validation.

Rollback is always: remove/comment the `model_catalog_json` line, restore the
backed-up `config.toml` if necessary, and fully restart Codex Desktop. The
custom catalog can remain on disk because it is inert when no config points to
it.

## 4. Restart and prove native v2 end to end

Fully exit Codex Desktop, including its background/tray process, then reopen it.
Do not assume CLI validation proved Desktop compatibility. Use the native agent
tool—not `codex exec`—with:

```text
model: gpt-5.6-luna
reasoning_effort: xhigh
fork_turns: none
goal: one harmless bounded task with an explicit terminal condition
```

Success requires all three receipts:

- Native spawn accepts `gpt-5.6-luna`.
- Luna returns the correct terminal result.
- The native agent tree reports the child as `completed`, not running.

If the native tool still lists only Sol and Terra, confirm the desktop process
was fully restarted and that `config.toml` points to the validated custom
catalog. If that remains true, roll back: the active Desktop build is not proven
compatible. Do not mistake a successful CLI Luna run for native v2 success.

Before using a Terra-manager-to-Luna-worker hierarchy, separately probe that
the active runtime permits nested spawning and has sufficient capacity. A
successful root-to-Luna probe proves only direct children.
