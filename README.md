# Autonomous Supermarket Operations Agent

A conversational AI-powered retail operations system for Kirana and supermarket stores.

The system allows store operators to manage **inventory, billing, GST calculations, product matching, and customer Khata credit** using natural language through Telegram.

Unlike a traditional CRUD-based application, it follows an **Observe → Reason → Act → Verify** agent workflow, where the LLM understands the request and invokes business tools, while critical validations remain inside deterministic service logic.

## Key Features

* Agent-based natural language operations
* Stateful multi-turn billing
* Inventory tracking and oversell protection
* Product normalization and fuzzy matching
* GST calculation
* Customer Khata credit ledger
* Telegram Bot interface
* Gemini as primary LLM
* Groq Llama 3.3 70B as fallback
* Async SQLAlchemy with SQLite
* Business rules enforced outside the LLM

## Architecture

```text
Telegram
   |
   v
Agent Orchestrator
Observe -> Reason -> Act -> Verify
   |
   +-------------------+
   |                   |
Gemini              Groq
Primary             Fallback
   |                   |
   +---------+---------+
             |
         Tool Layer
             |
   +---------+---------+
   |         |         |
Inventory  Billing   Khata
Service    Service   Service
   |         |         |
   +---------+---------+
             |
      SQLAlchemy Async
             |
           SQLite
```

## Tech Stack

| Area         | Technology           |
| ------------ | -------------------- |
| Language     | Python               |
| Primary LLM  | Google Gemini        |
| Fallback LLM | Groq / Llama 3.3 70B |
| Interface    | Telegram Bot API     |
| ORM          | SQLAlchemy Async     |
| Database     | SQLite               |
| Architecture | Agent + Tool Calling |

## Current Status

### Implemented

* Inventory management
* Multi-turn billing
* Product resolution
* GST calculations
* Khata management
* LLM failover
* Telegram integration

### Planned

* PDF GST invoice generation
* PowerPoint sales analytics
* PostgreSQL migration
* Redis session management
* Demand forecasting
* Automated stock alerts

## Core Design Principle

> The LLM understands and selects the operation, but deterministic business services validate and modify the actual business state.

This reduces hallucination risk and makes the system safer for transactional retail operations.

## Author

**Dhiraj Bhandari**
B.Tech Artificial Intelligence & Data Science
