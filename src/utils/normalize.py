"""Term normalization for ontology candidate deduplication."""

import re


def normalize_term(term: str) -> str:
    """Collapse surface forms to a canonical key for candidate grouping.

    Rules:
    - strip parenthetical content: "xxx (yyy)" → "xxx"
    - strip leading articles: "the xxx" → "xxx"
    - lowercase
    - strip hyphens and spaces
    - collapse 'v' before digits (BGPv4 → bgp4)

    Examples:
        BGP-4       → bgp4
        BGP v4      → bgp4
        BGPv4       → bgp4
        MPLS-TE     → mplste
        IS-IS       → isis
        network layer reachability information (NLRI) → networklayerreachabilityinformation
        the BGP protocol → bgpprotocol
    """
    t = term.strip()
    # Strip parenthetical content
    t = re.sub(r"\s*\([^)]*\)\s*", " ", t).strip()
    # Strip leading articles
    t = re.sub(r"^(the|a|an)\s+", "", t, flags=re.I)
    # Lowercase + strip hyphens/spaces
    t = t.lower()
    t = t.replace("-", "").replace(" ", "")
    t = re.sub(r"v(\d)", r"\1", t)
    return t


def extract_abbreviation(term: str) -> str | None:
    """Extract abbreviation from parenthetical if present.

    "network layer reachability information (NLRI)" → "NLRI"
    "Border Gateway Protocol (BGP)" → "BGP"
    "simple text" → None
    """
    m = re.search(r"\(([A-Za-z][A-Za-z0-9\-]{0,10})\)\s*$", term)
    return m.group(1) if m else None