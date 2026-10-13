"""User-triggered name resolution with bounded network requests."""

import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from molecules.chemistry.adapter import from_smiles
from molecules.domain.document import Source

# Small, explicit offline convenience dictionary. No guesses for unknown names.
COMMON_NAMES = {
    "water": "O",
    "ethanol": "CCO",
    "methanol": "CO",
    "acetone": "CC(=O)C",
    "benzene": "c1ccccc1",
    "acetic acid": "CC(=O)O",
    "toluene": "Cc1ccccc1",
    "aspirin": "CC(=O)Oc1ccccc1C(=O)O",
    "caffeine": "Cn1c(=O)c2c(ncn2C)n(C)c1=O",
    "phenol": "Oc1ccccc1",
    "ammonia": "N",
    "cyclohexane": "C1CCCCC1",
    "pyridine": "c1ccncc1",
    "ethyl acetate": "CCOC(=O)C",
    "formaldehyde": "C=O",
}


def resolve(query: str, mode: str = "Name"):
    query = query.strip()
    if not query or len(query) > 2000:
        raise ValueError("Enter a name or SMILES of at most 2,000 characters.")
    warning = ""
    if mode == "SMILES":
        smiles, provider = query, "SMILES input"
    elif query.casefold() in COMMON_NAMES:
        smiles, provider = COMMON_NAMES[query.casefold()], "Built-in name library (offline)"
    else:
        url = "https://www.ebi.ac.uk/opsin/ws/" + quote(query, safe="") + ".json"
        try:
            request = Request(
                url, headers={"Accept": "application/json", "User-Agent": "Molecules/0.2"}
            )
            with urlopen(request, timeout=12) as response:
                content = response.read(2 * 1024 * 1024 + 1)
            if len(content) > 2 * 1024 * 1024:
                raise ValueError("The name service response was too large.")
            payload = json.loads(content)
            if payload.get("status") not in ("SUCCESS", "WARNING") or not payload.get("smiles"):
                raise ValueError(payload.get("message") or "OPSIN could not interpret this name.")
            smiles, provider = payload["smiles"], "OPSIN · EMBL-EBI"
            warning = "; ".join(payload.get("warnings", []))
        except HTTPError as exc:
            raise ValueError(
                "OPSIN could not resolve this name. Try a systematic name or SMILES."
            ) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise ValueError(
                "Name lookup is unavailable. Retry, use a built-in name, or enter SMILES."
            ) from exc
    document = from_smiles(smiles, query)
    document.sources = [Source(query, provider, smiles, [a.id for a in document.atoms])]
    return document, warning
