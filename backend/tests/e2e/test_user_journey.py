"""E2E: a full session driven entirely through the public API, as the
extension + dashboard would drive it. Real DB, real routers, real pgvector
query; only the embedding model is stubbed. The digest is now LLM-free.
"""
import pytest

pytestmark = pytest.mark.e2e


def test_log_review_and_digest_journey(client):
    # health check the dashboard pings
    assert client.get("/health").json() == {"status": "ok"}

    # 1. rate two submissions (as the browser extension does)
    r1 = client.post("/api/attempts", json=dict(
        url="https://leetcode.com/lis", title="Longest Increasing Subsequence",
        platform="leetcode", tags="dynamic programming,arrays", rating=5, solved_self=False))
    assert r1.status_code == 200
    pid = r1.json()["problem_id"]

    client.post("/api/attempts", json=dict(
        url="https://codeforces.com/g1", title="BFS Grid",
        platform="codeforces", tags="graphs,bfs", rating=2, solved_self=True))

    # 2. the dashboard lists everything, then filters to the hard/unaided ones
    assert len(client.get("/api/problems").json()) == 2
    hard = client.get("/api/problems?min_rating=4&solved_self=false").json()
    assert len(hard) == 1 and hard[0]["id"] == pid

    # 3. overview tiles
    ov = client.get("/api/stats/overview").json()
    assert ov["total_problems"] == 2
    assert ov["hard_rated_count"] == 1
    assert ov["solved_self_count"] == 1

    # 4. "find similar to this one I struggled with" + free-text pre-check
    assert client.get(f"/api/problems/{pid}/similar").status_code == 200
    txt = client.get("/api/problems/search-similar-text",
                     params={"text": "dynamic programming,arrays"}).json()
    assert txt[0]["url"] == "https://leetcode.com/lis"  # matches by tag embedding

    # 5. weekly digest on demand
    digest_body = client.post("/api/stats/digest/send-now").json()
    assert digest_body["stats"]["total"] == 2
    assert isinstance(digest_body["note"], str) and digest_body["note"]

    # 6. edit then delete
    assert client.patch(f"/api/problems/{pid}", json={"rating": 4}).status_code == 200
    assert client.delete(f"/api/problems/{pid}").status_code == 204
    assert len(client.get("/api/problems").json()) == 1
