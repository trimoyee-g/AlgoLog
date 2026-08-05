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

**Study material shares the same Postgres.** Uploaded PDFs are chunked into the `chunks` table
next to `problems.embedding`, so passage search and "find similar problems" run on one engine and
one transaction. A document store alongside pgvector would mean either a second vector engine or
a cross-store join with no foreign key — and no way to rank one corpus against the other.

**The cross-encoder grades; the LLM only decides and writes.** Retrieval is a bi-encoder, which
embeds question and passage *independently* — it cannot see them together, which is exactly the
signal a grading step is supposed to add. A cross-encoder scores them jointly, so it supplies
information the retriever structurally lacks. Asking a small chat model to score passages one by
one is a slower, worse imitation of that: ~20 generations to reproduce what one batched CPU call
gives. The chat model is left with the routing decision and the query rewrite — one call each,
which is what generation is actually for.

**The relevance floor is calibrated, not assumed.** ms-marco logits are not centred on zero: a
clearly relevant passage measured **−7.7** while irrelevant ones clustered near **−11.2**. A
floor of `0.0` discarded every real hit and sent every question to the web fallback. What the
model gets reliably right is the *ordering*; `MIN_SCORE` only has to clear the junk cluster.
Re-measure it if the corpus changes shape — the numbers are in `services/crag.py`.
