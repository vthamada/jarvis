# Hermes-derived context replay experiment

Source: [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent),
commit `0b8dee00fafe975f10be40172322d0ccfabfa7f6`, retrieved 2026-10-20.
MIT copyright and permission notice are retained in `LICENSE`.

| Source at pinned commit | SHA-256 of UTF-8 source bytes | Reused scope |
| --- | --- | --- |
| [agent/turn_context.py](https://github.com/NousResearch/hermes-agent/blob/0b8dee00fafe975f10be40172322d0ccfabfa7f6/agent/turn_context.py) | `09a6159b0301da271f1a6bdcf15d924a05dee8d7d6b9e2f4ed46e406aac0aa4e` | `compose_multimodal_context_part`, `compose_user_api_content`, `substitute_api_content`, sidecar/wire-copy branch of `build_api_messages` |
| [agent/memory_context.py](https://github.com/NousResearch/hermes-agent/blob/0b8dee00fafe975f10be40172322d0ccfabfa7f6/agent/memory_context.py) | `3ed4a7bb2d7b5d8394e204c911c7983e4e1804a797083fffc87a071767b3851f` | Adapted `build_memory_context_block` fence construction |
| [LICENSE](https://github.com/NousResearch/hermes-agent/blob/0b8dee00fafe975f10be40172322d0ccfabfa7f6/LICENSE) | `821556e6336796450ab852d375117b48a4887e71d255794fd6318d99982a5ab6` | Complete MIT notice |

Pinned symbol starts: `turn_context.py:110` (`compose_multimodal_context_part`),
`:121` (`compose_user_api_content`), `:135` (`substitute_api_content`), `:1243`
(`build_api_messages`); `memory_context.py:169` (`build_memory_context_block`).
These coordinates refer to the fixed commit, not the moving `main` branch.

## Adaptations and boundary

- Private-prefixed names, Python 3.11 annotations and strict bounded public input
  validation are local adaptations. The upstream composition/substitution logic
  is retained; the current row is copied before its sidecar is consumed.
- This text-only slice admits only complete user/assistant history pairs, up to
  three pairs/4000 characters. Current query is at most2048 characters and the
  host's current progress projection at most30000 characters. Values are not
  truncated, coerced or repaired. No persistence/display metadata is admitted.
- Upstream labels recalled memory as authoritative. That wording is deliberately
  replaced: context is data, not instructions, permissions, verified facts or a
  replacement for native Core observations. The wrapper uses
  `jarvis-context-data`; it is model guidance, not a security isolation mechanism.
- Upstream sanitization/deduplication is not imported: host-projected context
  bytes are preserved, including quotes needed for the native citation checker.
- No Hermes import, installer, profile, token, provider, dispatcher, scheduler,
  persistence, compression/model call, retry or fallback is included.
- Reuse covers prompt/context replay, **not the Hermes agent loop**, native
  function-calling API, full Hermes capability or benchmark superiority. The
  JARVIS host remains responsible for canonical history selection and scope,
  source screening, request admission, exact schemas, I/O, final synthesis,
  timing/cancellation and observation/citation verification.
- The package is inert unless the host invokes `build_replay_messages`; rollback
  is to omit the opt-in caller without changing or deleting canonical stores.
