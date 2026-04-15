"""
Компактная выжимка DOM из сериализованного HTML для промпта codegen (VLM before-step).
Детерминированная сортировка кандидатов для локаторов (data-*, id, aria, role, …).
"""
from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple

# Совпадает с приоритетом в llm_steps.DATA_ATTR_PRIORITY (CSS [data-*] в codegen)
_DATA_ATTR_ORDER: Tuple[str, ...] = (
    "data-testid",
    "data-test",
    "data-cy",
    "data-qa",
    "data-id",
)
_DATA_IDX = {n: i for i, n in enumerate(_DATA_ATTR_ORDER)}


def _data_attr_sort_key(name: str) -> Tuple[int, str]:
    return (_DATA_IDX.get(name, len(_DATA_ATTR_ORDER)), name)


def _strip_scripts_and_styles(html: str) -> str:
    if not html:
        return ""
    out = re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    out = re.sub(r"<style\b[^>]*>.*?</style>", "", out, flags=re.DOTALL | re.IGNORECASE)
    return out


def _candidate_score(attrs: Dict[str, str]) -> int:
    """Выше = лучше для локатора; 0 = не кандидат."""
    best = 0
    for k, v in attrs.items():
        if not v or not str(v).strip():
            continue
        kl = k.lower()
        if kl.startswith("data-"):
            tier, _ = _data_attr_sort_key(kl)
            if tier < len(_DATA_ATTR_ORDER):
                best = max(best, 500 - tier * 10 + min(len(str(v)), 50))
            else:
                best = max(best, 200 + min(len(str(v)), 30))
        elif kl == "id":
            best = max(best, 400 + min(len(str(v)), 40))
        elif kl in ("aria-label", "name", "placeholder"):
            best = max(best, 350 + min(len(str(v)), 40))
        elif kl == "role":
            best = max(best, 300)
        elif kl == "href" and str(v).strip() not in ("#", ""):
            best = max(best, 250)
    return best


class _LocatorCandidateCollector(HTMLParser):
    def __init__(self, max_tags: int) -> None:
        super().__init__()
        self._max_tags = max_tags
        self._tag_order = 0
        self.candidates: List[Dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        if len(self.candidates) >= self._max_tags * 3:
            return
        self._tag_order += 1
        raw: Dict[str, str] = {}
        for k, v in attrs:
            if k and v is not None:
                raw[k.lower()] = str(v)[:500]
        if not raw:
            return
        sc = _candidate_score(raw)
        if sc <= 0:
            return
        interesting = {
            k: v
            for k, v in raw.items()
            if (
                k.startswith("data-")
                or k
                in (
                    "id",
                    "role",
                    "name",
                    "type",
                    "href",
                    "aria-label",
                    "placeholder",
                    "alt",
                    "title",
                )
            )
        }
        if not interesting:
            return
        snippet = f"<{tag}"
        for k in sorted(interesting.keys()):
            val = interesting[k].replace('"', "&quot;")[:200]
            snippet += f' {k}="{val}"'
        snippet += ">"
        self.candidates.append(
            {
                "tag": tag.lower(),
                "attrs": interesting,
                "preview": snippet[:900],
                "_score": sc,
                "_order": self._tag_order,
            }
        )


def build_focused_dom_bundle(
    html: str,
    *,
    url: str = "",
    max_candidates: int = 40,
    max_snippet_chars: int = 8000,
) -> Dict[str, Any]:
    """
    Возвращает JSON-совместимый dict: candidates (отсортированы), html_snippet (обрезанный).
    """
    html = html or ""
    collector = _LocatorCandidateCollector(max_candidates * 2)
    try:
        collector.feed(html)
    except Exception:
        pass

    cands = collector.candidates
    cands.sort(key=lambda x: (-x["_score"], x["_order"]))
    out_c: List[Dict[str, Any]] = []
    for c in cands[:max_candidates]:
        out_c.append(
            {
                "tag": c["tag"],
                "attrs": c["attrs"],
                "preview": c["preview"],
                "score": int(c["_score"]),
            }
        )

    stripped = _strip_scripts_and_styles(html)
    if len(stripped) > max_snippet_chars:
        snippet = stripped[:max_snippet_chars] + "\n...[html_snippet truncated]"
    else:
        snippet = stripped

    return {
        "url": url or "",
        "candidates": out_c,
        "html_snippet": snippet,
    }


def focused_dom_bundle_to_prompt_text(bundle: Dict[str, Any], max_chars: int) -> str:
    """Текст для user message LLM: JSON с url и candidates (без полного html_snippet)."""
    try:
        text = json.dumps(
            {"url": bundle.get("url", ""), "candidates": bundle.get("candidates", [])},
            ensure_ascii=False,
        )
    except (TypeError, ValueError):
        text = "{}"
    if len(text) > max_chars:
        return text[:max_chars] + "\n...[focused dom truncated]"
    return text
