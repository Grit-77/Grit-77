<p align="center">
  <img src="./assets/grit-header-baroque.png" width="100%" alt="GRIT. Memory and a ledger for your agents.">
</p>

<p align="center">
  <a href="https://x.com/Grit_77"><b>X</b></a> &nbsp; / &nbsp;
  <a href="https://www.instagram.com/ismt.aydin"><b>Instagram</b></a>
</p>

<br>

I'm **Ismet**. I build **Grit**, a task ledger and shared memory for AI coding agents. It decides who owns a task, counts every attempt, and refuses "done" without evidence.

I share the build on [X](https://x.com/Grit_77).

## Grit

Grit sits between Claude Code, Codex, OMP and Hermes. Each agent gets the same ledger, the same memory and the same rules, enforced in Python rather than in a prompt. One person, Windows first, with worker servers for the heavy runs.

**The codebase is currently private** while the licence is decided. Early access: message me on X.

## How it works

| Rule | What it means |
| :--- | :--- |
| One owner | A task carries a lease and a fence token. It never runs in two places; a stale owner's result is refused. |
| Counted attempts | Three worker attempts, then three takeovers. Changing model, session or machine does not reset the counter. |
| Evidence before done | The acceptance command is re-run against the task's own tree. Its output is the evidence. No record, no done. |

## Numbers

| Measure | Value | Measured |
| :--- | :--- | :--- |
| Test suite | 10,398 passing | 2026-09-23, full suite on a Linux worker server |
| Harnesses | 4 | Claude Code, Codex, OMP and Hermes, one ledger, one rule set |

---

<p align="center">
  Push. Verify. Record.<br>
  <sub>Türkçe: yapay zekâ kodlama ajanları için görev defteri ve ortak hafıza. Türkçe yazılar ve videolar yolda.</sub>
</p>
