"""Parse Zotero RDF files and extract metadata and attachment relationships."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from xml.etree import ElementTree

NS = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "bib": "http://purl.org/net/biblio#",
    "z": "http://www.zotero.org/namespaces/export#",
    "link": "http://purl.org/rss/1.0/modules/link/",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "prism": "http://prismstandard.org/namespaces/1.2/basic/",
}

BIBLIO_ITEM_TYPES = {"preprint", "journalArticle", "bookSection", "conferencePaper", "thesis", "report", "webpage"}


def _text(el: ElementTree.Element, ns: str, tag: str) -> str:
    child = el.find(f"{{{NS.get(ns, '')}}}{tag}")
    if child is None:
        return ""
    val_el = child.find(f"{{{NS['rdf']}}}value")
    if val_el is not None and val_el.text:
        return val_el.text.strip()
    if child.text:
        return child.text.strip()
    return ""


def _element_id(el: ElementTree.Element) -> str:
    return el.attrib.get(f"{{{NS['rdf']}}}about", "")


def _extract_authors(entry_el: ElementTree.Element) -> list[str]:
    authors: list[str] = []
    for person in entry_el.findall(f".//{{{NS['foaf']}}}Person"):
        surname = _text(person, "foaf", "surname")
        given = _text(person, "foaf", "givenName")
        if surname and surname.strip().lower() == "others":
            continue
        if surname:
            name = f"{surname}, {given}" if given else surname
            authors.append(name)
    if authors:
        return authors
    for creator in entry_el.findall(f".//{{{NS['dc']}}}creator"):
        for li in creator.findall(f".//{{{NS['rdf']}}}li"):
            if li.text and li.text.strip():
                authors.append(li.text.strip())
        if not authors and creator.text and creator.text.strip():
            authors.append(creator.text.strip())
    return authors


def _get_item_type(el: ElementTree.Element) -> str:
    t = _text(el, "z", "itemType")
    if t:
        return t
    tag = el.tag.rsplit("}", 1)[-1] if "}" in el.tag else el.tag
    return tag.lower()


def _is_biblio_entry(el: ElementTree.Element) -> bool:
    itype = _get_item_type(el)
    return itype in BIBLIO_ITEM_TYPES


def _build_att_map(root: ElementTree.Element) -> dict[str, list[dict]]:
    """Build map: entry_id -> [attachment info dicts]."""
    att_map: dict[str, list[dict]] = {}
    # First pass: collect all attachment elements (z:Attachment or rdf:Description with type=attachment)
    attachment_by_id: dict[str, tuple[str, str]] = {}  # attach_id -> (path, type)
    for el in root.iter():
        tag = el.tag.rsplit("}", 1)[-1] if "}" in el.tag else el.tag
        el_id = _element_id(el)
        if tag == "Attachment":
            # z:Attachment: path in rdf:resource attribute of z:path
            path_el = el.find(f"{{{NS['z']}}}path")
            path = ""
            if path_el is not None:
                path = path_el.attrib.get(f"{{{NS['rdf']}}}resource", path_el.text or "")
            attach_type = _text(el, "dc", "type")
            attachment_by_id[el_id] = (path, attach_type)
        elif tag == "Description" and _get_item_type(el) == "attachment":
            path_el = el.find(f"{{{NS['z']}}}path")
            path = ""
            if path_el is not None:
                path = path_el.attrib.get(f"{{{NS['rdf']}}}resource", path_el.text or "")
            attach_type = _text(el, "dc", "type") or _text(el, "z", "linkMode")
            attachment_by_id[el_id] = (path, attach_type)

    # Second pass: link attachments to entries
    # Modern format: link:link inside entry points to attachment
    for el in root.iter():
        tag = el.tag.rsplit("}", 1)[-1] if "}" in el.tag else el.tag
        entry_id = _element_id(el)
        if not entry_id:
            continue
        is_entry = (tag in ("Entry", "Article") or (tag == "Description" and _is_biblio_entry(el)))
        if not is_entry:
            continue
        for link_el in el.findall(f".//{{{NS['link']}}}link"):
            attach_id = link_el.attrib.get(f"{{{NS['rdf']}}}resource", "")
            if attach_id in attachment_by_id:
                path, atype = attachment_by_id[attach_id]
                att_map.setdefault(entry_id, []).append({"path": path, "type": atype})

    # Legacy format: link:link inside attachment points to entry
    entry_ids = set()
    for el in root.iter():
        tag = el.tag.rsplit("}", 1)[-1] if "}" in el.tag else el.tag
        eid = _element_id(el)
        if tag in ("Entry", "Article") or (tag == "Description" and _is_biblio_entry(el)):
            entry_ids.add(eid)
    for el in root.iter():
        tag = el.tag.rsplit("}", 1)[-1] if "}" in el.tag else el.tag
        att_id = _element_id(el)
        if tag == "Attachment" or (tag == "Description" and _get_item_type(el) == "attachment"):
            for link_el in el.findall(f".//{{{NS['link']}}}link"):
                linked_entry = link_el.attrib.get(f"{{{NS['rdf']}}}resource", "")
                if linked_entry in entry_ids and att_id in attachment_by_id:
                    path, atype = attachment_by_id[att_id]
                    att_map.setdefault(linked_entry, []).append({"path": path, "type": atype})

    return att_map


def parse_rdf(path: Path) -> list[dict]:
    tree = ElementTree.parse(path)
    root = tree.getroot()

    att_map = _build_att_map(root)

    # Collect all bibliographic entry elements
    entries: list[ElementTree.Element] = []
    # bib:Entry (legacy test fixture format)
    entries.extend(root.findall(f".//{{{NS['bib']}}}Entry"))
    # z:Entry
    entries.extend(root.findall(f".//{{{NS['z']}}}Entry"))
    # bib:Article (common real format)
    entries.extend(root.findall(f".//{{{NS['bib']}}}Article"))
    # rdf:Description with bibliographic itemType (preprint, etc.)
    for desc in root.findall(f".//{{{NS['rdf']}}}Description"):
        if _is_biblio_entry(desc):
            entries.append(desc)

    items: list[dict] = []
    for entry_el in entries:
        entry_id = _element_id(entry_el)
        title = _text(entry_el, "dc", "title")
        abstract = _text(entry_el, "dcterms", "abstract")
        date = _text(entry_el, "dc", "date") or _text(entry_el, "dcterms", "dateSubmitted")
        authors = _extract_authors(entry_el)

        identifiers: dict[str, str] = {}
        # DOI / arXiv from dc:identifier (text or nested rdf:value)
        for ident_el in entry_el.findall(f".//{{{NS['dc']}}}identifier"):
            text = ident_el.text or ""
            if not text:
                val_el = ident_el.find(f"{{{NS['rdf']}}}value")
                text = val_el.text if val_el is not None and val_el.text else ""
            text = text.strip()
            # Handle DOI 10.xxx / DOI prefix
            doi_text = text
            if doi_text.upper().startswith("DOI "):
                doi_text = doi_text[4:].strip()
            if doi_text.startswith("10."):
                # DataCite arXiv DOI: 10.48550/arXiv.XXXX.XXXXX
                arxiv_in_doi = re.search(r"10\.\d{4,}/[Aa]r[Xx]iv[./-](\d{4}\.\d{4,5}(?:v\d+)?)", doi_text)
                if arxiv_in_doi:
                    identifiers.setdefault("arxiv", arxiv_in_doi.group(1))
                else:
                    identifiers.setdefault("doi", doi_text)
            # arXiv URL: http://arxiv.org/abs/XXXX.XXXXX
            arxiv_url = re.search(r"arxiv\.org/abs/(\d{4}\.\d{4,5}(?:v\d+)?)", text, re.IGNORECASE)
            if arxiv_url:
                identifiers.setdefault("arxiv", arxiv_url.group(1))
            elif "arxiv" in text.lower() and not identifiers.get("arxiv"):
                ids = text.replace("arXiv:", "").replace("DOI", "").strip()
                identifiers.setdefault("arxiv", ids)

        # arXiv ID from dc:description (format: "arXiv:XXXX" or "_eprint: XXXX")
        # dc:description is more reliable than dc:identifier for arXiv IDs — overwrite previous value
        for desc in entry_el.findall(f".//{{{NS['dc']}}}description"):
            if desc.text:
                text = desc.text.strip()
                arxiv_match = re.search(r"(?:arXiv:)?(\d{4}\.\d{4,5}(?:v\d+)?)", text, re.IGNORECASE)
                if not arxiv_match:
                    arxiv_match = re.search(r"_eprint:\s*(\d{4}\.\d{4,5}(?:v\d+)?)", text, re.IGNORECASE)
                if arxiv_match:
                    identifiers["arxiv"] = arxiv_match.group(1)
                elif text.startswith("10."):
                    identifiers.setdefault("doi", text)

        journal = (
            _text(entry_el, "prism", "publicationName")
            or _text(entry_el, "dcterms", "isPartOf")
            or _text(entry_el, "bib", "Journal")
            or _text(entry_el, "bib", "isPartOf")
        )
        # bib:isPartOf for articles may be a nested bib:Journal reference
        journal_el = entry_el.find(f"{{{NS['bib']}}}isPartOf")
        if journal_el is not None and not journal:
            journal = _text(journal_el, "dc", "title")
        year = date[:4] if date else ""
        citation_key = _text(entry_el, "z", "citationKey")

        items.append(
            {
                "title": title,
                "authors": authors,
                "date": date,
                "year": year,
                "abstract": abstract[:500] if abstract else "",
                "identifiers": identifiers,
                "journal": journal.strip() if journal else "",
                "citation_key": citation_key,
                "attachments": att_map.get(entry_id, []),
                "entry_id": entry_id,
            }
        )
    return items


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse Zotero RDF file")
    parser.add_argument("--rdf", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    items = parse_rdf(Path(args.rdf))
    if args.json:
        print(json.dumps(items, indent=2, ensure_ascii=False))
    else:
        for item in items:
            print(f"title: {item['title'][:100]}")
            count = len(item["authors"])
            print(f"authors: {item['authors'][:3]}... ({count} total)")
            print(f"date: {item['date']}")
            print(f"identifiers: {item['identifiers']}")
            for att in item["attachments"]:
                print(f"  attachment: {att['path']} (type={att['type']})")
            print()
    print(f"{len(items)} entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
