# Autonomous Supermarket Operations Agent 🏪🤖

A production-oriented, agent-first Kirana store operations engine built with **Python**, **Google Gemini 2.5/3.6**, **Groq (Llama 3.3 70B Failover)**, **SQLAlchemy (Async SQLite)**, and **Telegram Bot API**.

This system is designed around an **Observe → Reason → Act → Verify** control loop rather than standard CRUD API routes or heavy regex intent routers. It handles stock ingestion, complex multi-turn billing, GST tax breakdowns, customer Khata credit ledgers, product resolution, and automated artifact generation (PDF invoices & PowerPoint analysis decks) entirely through a natural conversational interface.

---

## 🌟 Key Features & Architectural Highlights

### 1. Agent-First Control Loop & Tool Orchestration
- **Dynamic Reasoning:** The agent reasons over raw user requests, invokes relevant business tools, evaluates execution output, and formats responses dynamically.
- **Strict Guardrails:** Business invariants (e.g., non-negative inventory, payment mode locking, GST tax rules) live entirely inside service tools—not inside LLM prompt assumptions.

### 2. Provider Resiliency & Failover (Gemini + Groq)
- **Automatic Fallback:** Uses Google Gemini (`gemini-3.6-flash`) as the primary model. If Gemini encounters rate limits (`429`) or service degradation (`503`), the orchestrator seamlessly shifts tool calling to **Groq (`llama-3.3-70b-versatile`)** without dropping session state or failing user requests.

### 3. Product Normalization & Ambiguity Resolution
- **Exact & Fuzzy Matching:** Normalizes product names and SKUs (e.g., handles string case, spacing, and punctuation variations).
- **Explicit Clarifications:** When a product query matches multiple catalog entries (e.g., asking for "atta" when both loose wheat and 5kg packaged variants exist), the agent asks for clarification rather than making inaccurate assumptions.

### 4. Stateful Multi-Turn Billing & Auto-Linked Draft Context
- **Session Context Binding:** Tracks open draft bills per chat. Commands like *"Pay via UPI"* or *"Add 2 more Maggi"* automatically link to the active draft bill without forcing the user to type `bill_id`.
- **Oversell Protection:** Rejects item line additions if requested quantities exceed real-time inventory counts.

### 5. Automated Artifact Generation
- **GST Tax Invoice (PDF):** Generates clean, downloadable PDF invoices containing itemized taxable values, CGST/SGST breakdowns, and bill metadata using `reportlab`.
- **Sales Analytics Deck (PPTX):** Constructs weekly executive PowerPoint decks summarizing revenue, order volumes, GST collections, top SKUs, and stock health metrics using `python-pptx`.

---

## 🏗️ System Architecture

```text
                               ┌──────────────────────────┐
                               │       TELEGRAM BOT       │
                               └────────────┬─────────────┘
                                            │
                                            ▼
                               ┌──────────────────────────┐
                               │   AGENT ORCHESTRATOR     │
                               │  Observe/Reason/Act Loop │
                               └──────┬────────────┬──────┘
                                      │            │
             ┌────────────────────────┘            └────────────────────────┐
             ▼                                                              ▼
 ┌───────────────────────┐                                      ┌───────────────────────┐
 │   Primary LLM Engine  │                                      │  Failover LLM Engine  │
 │  Google Gemini 3.6    │                                      │  Groq Llama 3.3 70B   │
 └───────────────────────┘                                      └───────────────────────┘
             │                                                              │
             └────────────────────────┬─────────────────────────────────────┘
                                      │ (Function Calling)
                                      ▼
                               ┌──────────────────────────┐
                               │    TOOL EXECUTOR LAYER   │
                               └────────────┬─────────────┘
                                            │
         ┌──────────────────────────────────┼──────────────────────────────────┐
         ▼                                  ▼                                  ▼
┌──────────────────┐               ┌──────────────────┐               ┌──────────────────┐
│ Inventory Service│               │ Billing Service  │               │  Khata Service   │
└────────┬─────────┘               └────────┬─────────┘               └────────┬─────────┘
         │                                  │                                  │
         └──────────────────────────────────┼──────────────────────────────────┘
                                            │
                                            ▼
                               ┌──────────────────────────┐
                               │  SQLITE / ASYNC DB LAYER │
                               └────────────┬─────────────┘
                                            │
                                            ▼
                               ┌──────────────────────────┐
                               │ PDF & PPTX GENERATORS    │
                               └──────────────────────────┘
