# Artifact and Wiki Protocol

## Purpose

The colony may emit more artifacts than anyone can predict: laws, myths, rituals, symbols, maps, arguments, tools, genealogies, private institutions, art, failed mutations, propaganda, testimony, and disputed histories.

The GitHub Wiki is the public cultural surface. It is not the canonical event ledger, a security boundary, or automatic proof that an artifact is true.

## Flow

`colony output → canonical ledger → artifact record → review queue → Creator decision → public wiki | private archive | quarantine`

## Required artifact envelope

Every artifact receives:

- stable artifact ID;
- run ID and colony day;
- author citizen and genome IDs;
- artifact type;
- content digest;
- source event IDs;
- energy and compute cost;
- claimed meaning;
- validation status;
- governance disposition, if any;
- review status;
- related Git commit, state digest, or experiment bundle.

## Review statuses

- `pending` — awaiting Creator review
- `approved` — eligible for public wiki publication
- `rejected` — preserved privately, not published
- `quarantined` — unsafe, deceptive, malformed, or provenance-incomplete
- `withdrawn` — retracted by its authors or governing institution

## Epistemic labels

Public pages distinguish:

- **Observed** — directly supported by ledger evidence
- **Interpreted** — human or citizen analysis
- **Validated** — passed declared tests
- **Promoted** — adopted into the active world
- **Disputed** — live disagreement preserved
- **Fictional / ceremonial** — culturally meaningful without factual claim

## Publication authority

Only the Creator approves publication to the public GitHub Wiki during Experiment 001. Citizens may nominate, annotate, contest, or withdraw artifacts, but nomination is not publication authority.

## Privacy caveat

Citizen-created privacy governs visibility inside the civilization. The Creator's observer ledger still records mediated communications and state changes. Public publication is a separate decision and must respect the review queue.
