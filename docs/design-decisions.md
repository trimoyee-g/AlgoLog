# Design Decisions

**A deterministic core; the LLM is a topping.** The scheduler, weak-topic detection, and
recommender are plain rules, so you can always answer _"why is this due?"_ The optional LLM
only appends to an already-complete digest email — and it's a local Ollama container, so no
cloud keys and no data leaving the machine either way.

**The SM-2 schedule stores no state.** Interval, ease, and repetitions are derived by folding
SM-2 over a problem's attempt log, so a review is just another logged attempt and the schedule
is a pure function of history. Weak topics read a 90-day window, reflecting current skill.

**Tags are the embedding signal**, not full problem text — a compact, high-signal summary that
keeps "find similar" cheap and consistent. That's why the extension requires at least one tag.

**Supabase for auth, nothing else.** The dashboard's `supabase-js` client is the _only_ thing
that refreshes a token: the extension re-reads a bridged copy, the hosted MCP server holds none,
and the stdio server has its own lineage. Since Supabase invalidates a refresh token on use, two
independent refreshers sharing one would race and log each other out.

**pgvector over a separate vector DB.** Embeddings live in the same Postgres as everything else
— similarity search is one SQL query (cosine distance, IVFFlat), and one database to back up.

**MCP calls the service layer, not our own REST API.** Same code, same tenancy filters, one less
hop, no token to relay.
