# Autonomous Supermarket Operations Agent

An **AI-powered retail operations agent** that enables Kirana and supermarket stores to manage daily operations through natural language.

The system uses an **Observe → Reason → Act → Verify** control loop to handle inventory, billing, GST calculations, product resolution, and customer Khata management through a Telegram-based conversational interface.

## What It Does

A store operator can interact with the system naturally:

```text
"Add 2 Maggi and 1 packet of biscuits."

"How much stock is left?"

"Create a bill for Ravi."

"Pay the current bill using UPI."

"How much does Ravi owe?"
```

The agent determines the required operation, selects the appropriate business tool, executes it through the service layer, and verifies the result before responding.

## Key Features

* **Agentic Tool Calling** — LLM dynamically selects and executes business tools.
* **Multi-turn Billing** — Maintains active draft bills across conversations.
* **Inventory Management** — Tracks stock and prevents overselling.
* **Product Resolution** — Supports normalization, exact matching, fuzzy matching, and ambiguity handling.
* **GST Billing** — Performs deterministic GST and tax calculations.
* **Khata Management** — Maintains customer credit and payment records.
* **LLM Failover** — Automatically switches from Gemini to Groq when the primary provider is unavailable.
* **Telegram Interface** — Provides a simple conversational interface for store operators.

## Architecture

```text
                    Telegram
                       |
                       v
              Agent Orchestrator
            Observe → Reason → Act
                       |
              +--------+--------+
              |                 |
           Gemini              Groq
           Primary            Fallback
              |                 |
              +--------+--------+
                       |
                  Tool Calling
                       |
        +--------------+--------------+
        |              |              |
    Inventory       Billing         Khata
     Service        Service         Service
        |              |              |
        +--------------+--------------+
                       |
                SQLAlchemy Async
                       |
                    SQLite
```

## Technology Stack

* **Python**
* **Google Gemini**
* **Groq / Llama 3.3 70B**
* **Telegram Bot API**
* **SQLAlchemy (Async)**
* **SQLite**

## Important Design Decision

The LLM is responsible for **understanding requests and selecting tools**, but it does not directly control business-critical data.

Business rules such as:

```text
Requested quantity <= Available stock
GST calculations
Valid bill state
Valid payment transitions
```

are enforced inside deterministic service-layer logic.

This separation makes the system more reliable for transactional operations.

## Current Status

### Implemented

* Agent orchestration
* Gemini integration
* Groq failover
* Telegram bot
* Inventory management
* Product resolution
* Stateful billing
* GST calculations
* Khata management
* Business-rule validation

### Planned

* PDF GST invoice generation
* PowerPoint sales analytics
* PostgreSQL support
* Redis-based session management
* Automated stock alerts
* Demand forecasting

## Project Vision

The goal is to build an **AI-native operational layer for small retail businesses**, where store owners can manage everyday operations through conversation instead of navigating complex software interfaces.

---

**Author:** Dhiraj Bhandari
**B.Tech — Artificial Intelligence & Data Science**
