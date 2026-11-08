# leash
Leash is a Solana program that lets you fund an AI agent with USDC under strict onchain rules: per-payment cap, daily cap, merchant allowlist, and instant revoke. The agent pays for APIs per request. The chain says no when it tries to overspend.
# Leash

Give your AI agent a budget, not your wallet. A Solana program enforces per-payment cap, daily cap,
a merchant allowlist and instant revoke on every payment an agent makes.

## Run it (devnet)

```bash
npm install
anchor build && anchor keys sync && anchor build && anchor deploy --provider.cluster devnet
# put the printed program id into Anchor.toml and programs/leash/src/lib.rs (declare_id!) first
PROGRAM_ID=<id> npm run setup     # test USDC, vault (0.10/tx, 1.00/day), funds it, writes state.json
npm run merchant                  # terminal 1: paid API on :4020 (402 flow)
npm run agent                     # terminal 2: pays 0.02 USDC and gets data
npm run attack                    # hijacked agent: both payments are rejected by the program
npm run revoke                    # owner kills the agent; the next `npm run agent` fails
```

Set `ANTHROPIC_API_KEY` to let Claude drive the agent (it calls a `buy_data` tool). Override the model
with `LEASH_MODEL`. Devnet airdrops are rate limited; if setup fails, retry or fund via a faucet.

## Layout

- `programs/leash/src/lib.rs`: Anchor program (create_vault, pay, revoke, withdraw)
- `src/leash.ts`: client that hand-encodes instructions, plus `fetchWithLeash` for HTTP 402
- `src/merchant.ts`: demo paid API that verifies the onchain payment and memo
- `src/agent.ts`: the agent (LLM mode, scripted mode, `--attack`)
- `src/setup.ts`, `src/revoke.ts`: owner-side scripts

Devnet test keys only. Never commit `state.json`.
