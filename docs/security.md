# Security

Voice agents combine credentials, media, transcripts, tools, and user-supplied
input. Treat every boundary explicitly.

## Secrets

- Store local secrets in `.env.local`.
- Use a managed secret store in production.
- Never put credentials in examples, tokens, logs, screenshots, or exceptions.
- Rotate a credential immediately if it reaches Git history or a chat message.

Deleting a secret from the latest commit does not remove it from Git history.
Rotate first; history rewriting is secondary.

The included CI scans the current tree. After rewriting legacy Git history, run
a full-history Gitleaks scan locally or change the checkout depth back to `0`.

## LiveKit tokens

Generate participant tokens on a trusted backend. Scope grants to the required
room and capabilities, use unique identities, and keep expiration short.

## RPC

Do not trust an RPC method merely because the caller is in the room. Validate
`caller_identity`, authorize the requested operation, validate the JSON schema,
and rate-limit state-changing calls.

## Tools and handoffs

Validate tool arguments in Python. Prompts improve behavior but are not an
authorization layer. Require explicit confirmation for destructive or costly
actions.

## Conversation data

Transcripts and extracted contact details may be personal data. Define
retention, access control, encryption, deletion, and consent policies before
persisting them.

## XTTS

The sample XTTS endpoint uses plain HTTP because it is commonly deployed on a
private network. For public networks, use TLS, authentication, request limits,
and an allowlist. Treat speaker reference files as sensitive biometric data.
