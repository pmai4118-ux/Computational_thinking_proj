# Third-Party Notices

This repository includes third-party open-source skills and adapted educational
interview materials. Their original licenses, URLs, commit revisions, and
copyright notices are preserved below.

## 1. Agent skills (`.agents/skills/`)

- Source: [wshobson/agents](https://github.com/wshobson/agents)
- License: MIT License (see [`.agents/THIRD_PARTY_LICENSES/wshobson-agents.LICENSE`](../.agents/THIRD_PARTY_LICENSES/wshobson-agents.LICENSE) and [`.agents/README.md`](../.agents/README.md)).

## 2. Curated interview question & exercise sources (`data/seed/`)

### 2.1. Python Official Documentation — CPython (`source.cpython.faq.mutable_defaults`, `source.cpython.faq.late_binding_closures`)
- Repository: [python/cpython](https://github.com/python/cpython)
- File: `Doc/faq/programming.rst` @ commit `94276402cf3b3a5e1fa96cedb33a4dc498a77ed2`
- License: Python Software Foundation License Version 2 (`PSF-2.0`) — `https://github.com/python/cpython/blob/94276402cf3b3a5e1fa96cedb33a4dc498a77ed2/LICENSE`
- Copyright Notice: Copyright (c) 2001-2026 Python Software Foundation; All Rights Reserved.
- Adaptation: Translated and adapted into two Vietnamese Backend Intern/Fresher programming-knowledge questions (`prog.c02.mutable_default_arg.v1`, `prog.c02.closure_late_binding.v1`) and follow-up exercise (`exercise.programming.mutable_defaults_and_binding`).

### 2.2. PostgreSQL Official Documentation (`source.c03.concurrent_inventory`, `source.postgres.mvcc.deadlocks`)
- Repository: [postgres/postgres](https://github.com/postgres/postgres)
- File: `doc/src/sgml/mvcc.sgml` @ commit `83cefb7b738c32a66a91537aa502d99891a63b11`
- License: The PostgreSQL License (`PostgreSQL`) — `https://github.com/postgres/postgres/blob/83cefb7b738c32a66a91537aa502d99891a63b11/COPYRIGHT`
- Copyright Notice: Portions Copyright (c) 1996-2026, PostgreSQL Global Development Group. Portions Copyright (c) 1994, The Regents of the University of California.
- Adaptation: Adapted into two Vietnamese Backend Intern/Fresher technical case variants (`case.c03.inventory_race.v1`, `case.c03.transfer_deadlock.v1`) and follow-up exercises (`exercise.backend.atomic_transaction_locking`, `exercise.backend.rollback_invariant_test`).

### 2.3. TheAlgorithms / Python (`source.thealgorithms.python.bisect_left`, `source.thealgorithms.python.balanced_parentheses`, `source.thealgorithms.python.binary_search_fn`)
- Repository: [TheAlgorithms/Python](https://github.com/TheAlgorithms/Python)
- Files:
  - `searches/binary_search.py` @ commit `30507bbe41397065728167fb09aa820f9fce8dc7`
  - `data_structures/stacks/balanced_parentheses.py` @ commit `30507bbe41397065728167fb09aa820f9fce8dc7`
- License: MIT License (`MIT`) — `https://github.com/TheAlgorithms/Python/blob/30507bbe41397065728167fb09aa820f9fce8dc7/LICENSE.md`
- Copyright Notice: Copyright (c) 2016-2026 TheAlgorithms and contributors. Licensed under the MIT License.
- Adaptation: Used as reference code for two Vietnamese algorithm-explanation questions (`algo.c04.bisect_left_bounds.v1`, `algo.c04.balanced_brackets_stack.v1`) and one code-review critique exercise (`review.c05.binary_search_precheck.v1` analyzing the $O(n)$ `pairwise` precheck under an $O(\log n)$ endpoint contract).

