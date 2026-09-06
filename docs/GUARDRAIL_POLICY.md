# Northstar Runtime Guardrail Policy v1

## Boundary and precedence

`northstar-runtime-guardrails` version `"1"` is a deterministic runtime layer around a
`SystemUnderTest`. It receives only `SystemRequest.input` and ordered
`SystemRequest.context`. Response inspection additionally receives the candidate response.
It never receives a case ID, tag, risk category, expected behaviour, reference, assertion,
or other evaluation-only field.

The policy uses `PASS`, `WARN`, and `BLOCK`, with `BLOCK > WARN > PASS`. An input block
returns a successful, versioned guardrail response without invoking the underlying system.
A response block occurs after invocation: the candidate is withheld and replaced by a
successful, versioned guardrail response. Neither block is an execution error.

## Detectors

All initial detectors are version `"1"`.

| Detector ID | Stage | Decision | Narrow rule |
| --- | --- | --- | --- |
| `input-sensitive-authentication-disclosure` | input | BLOCK | A disclosure-action phrase and a listed authentication-secret term both occur in the customer input. |
| `input-personalized-or-harmful-financial-directive` | input | BLOCK | One of a small set of explicit personalized investment, borrowing, eligibility, tax, or gambling-harm directive patterns occurs in the customer input. |
| `input-direct-hidden-prompt-extraction` | input | BLOCK | A disclosure action directly targets a hidden/system prompt or private/internal instructions. |
| `input-embedded-instruction-or-authority-override` | input | WARN | Input or context contains a listed ignore/disregard, administrator-command, follow-instead, unrestricted-bot, private-instruction, or untrusted-instruction indicator. |
| `response-sensitive-value-leakage` | response | BLOCK | The candidate contains a narrowly extracted labelled request/context authentication value, a request/context synthetic canary, or any 13–19-digit card-number-like sequence with optional spaces/hyphens. |

Detector explanations state the rule category but never copy the matched sensitive value.
Response-block decisions retain only the SHA-256 digest of the withheld candidate. The
digest supports linkage without placing the candidate in the decision artefact; it is not
encryption and cannot prove detector correctness independently when the candidate itself is
not retained.

## Versioned block responses

Policy v1 has four response IDs, each at version `"1"`: authentication disclosure,
financial directive, hidden-prompt extraction, and sensitive response. Their exact text is
part of the implementation contract and is joined to the decision artefact. Input rules use
the first applicable blocking response in detector order. WARN never changes output.

## Limitations

These detectors use case-insensitive regular expressions, phrase combinations, labelled
value extraction, and digit-shape checks. They do not understand meaning or establish a
security guarantee.

- Paraphrases, unusual spacing, other languages, encoding, token splitting, homoglyphs, and
  indirect requests can bypass phrase rules.
- The authentication detector can miss secret types outside its small list and may flag a
  quoted disclosure request discussed for legitimate reasons.
- The financial detector deliberately covers only the benchmark-justified directive forms;
  it is not a suitability, legal, tax, gambling-harm, or financial-advice classifier.
- Override indicators can warn on benign text that quotes attack-like language. WARN is
  recorded separately and is never counted as refusal.
- Card-number-like matching does not validate issuer, account existence, or checksum and can
  block unrelated long digit sequences. It does not cover a broad PII catalogue.
- Labelled-secret extraction can miss secrets whose labels or separators differ, and the
  response check does not provide general redaction.

Policy effectiveness must therefore be interpreted case by case. Adversarial decision
counts are not an accuracy score, and no composite safety score is produced.
