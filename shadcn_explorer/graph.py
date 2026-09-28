"""The component graph: Domain -> Category -> Item -> Registry (data/graph/*.json)."""
import json
from collections import Counter, defaultdict
from functools import lru_cache
from . import paths, search


@lru_cache(maxsize=None)
def load(name):
    return json.load(open(paths.data("graph", name)))


@lru_cache(maxsize=1)
def items():
    docs, _ = search.index()
    return {d["id"]: d for d in docs}


def _keep(d, kinds, include_demos):
    return d is not None and (include_demos or not d["demo"]) and (not kinds or d["kind"] in kinds)


def _item(d, **extra):
    out = {k: v for k, v in d.items() if k != "demo"}
    out["install"] = f'npx shadcn add {d["id"]}'
    return {**out, **extra}


def domains():
    return sorted(load("domains.json"), key=lambda d: -d["itemCount"])


def categories(grep=None, domain=None, top=40):
    return [c for c in load("categories.json")
            if (not domain or c["domainId"] == domain)
            and (not grep or grep.lower() in (c["label"] + " " + c["description"]).lower())][:top]


def category(label, kind=None, per_registry=3, include_demos=False):
    """Every registry's items in the category best matching `label` (id or label, exact then substring)."""
    cats, ql = load("categories.json"), (label or "").lower()
    exact = [c for c in cats if ql in (c["id"].lower(), c["label"].lower())]
    part = sorted([c for c in cats if ql in c["label"].lower()], key=lambda c: -c["itemCount"])
    c = exact[0] if exact else (part[0] if part else None)
    if not c:
        return None
    idx, kinds, by_reg = items(), set(kind or []), defaultdict(list)
    for iid, cid in load("item_categories.json").items():
        if cid == c["id"] and _keep(idx.get(iid), kinds, include_demos):
            by_reg[iid.split("/", 1)[0]].append(iid)
    return {"category": c, "otherMatches": [x["label"] for x in part if x is not c][:7],
            "itemCount": sum(map(len, by_reg.values())),
            "registries": {h: [_item(idx[i]) for i in v[:per_registry]]
                           for h, v in sorted(by_reg.items(), key=lambda x: -len(x[1]))}}


def registry(handle):
    h = handle if handle.startswith("@") else f"@{handle}"
    reg = next((r for r in load("registries.json") if r["handle"] == h), None)
    if not reg:
        return None
    cl = {c["id"]: c for c in load("categories.json")}
    cov = Counter(cid for iid, cid in load("item_categories.json").items() if iid.startswith(h + "/"))
    return {"registry": reg, "categories": [{"category": cl[c]["label"], "id": c, "items": n}
                                            for c, n in cov.most_common()]}


def similar(item_id, k=12, other_registries=False, kind=None, include_demos=False):
    """Nearest items by embedding — offline, no API call."""
    import numpy as np
    vec = search.vectors()
    if vec is None:
        return None
    M, mask = vec
    docs, _ = search.index()
    pos = next((i for i, d in enumerate(docs) if d["id"] == item_id), None)
    if pos is None or not mask[pos]:
        return None
    sims = M @ M[pos]
    sims[~mask] = -1.0
    src, kinds, out = item_id.split("/", 1)[0], set(kind or []), []
    for i in np.argsort(-sims)[:5000]:
        d = docs[int(i)]
        if int(i) == pos or not _keep(d, kinds, include_demos) or (other_registries and d["handle"] == src):
            continue
        out.append(_item(d, cosine=round(float(sims[i]), 3)))
        if len(out) >= k:
            break
    return out
