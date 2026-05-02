# ⚡ Wumpus Logic Agent

A **Knowledge-Based AI Agent** that navigates a Wumpus World grid using **Propositional Logic** and **Resolution Refutation** — served as a fully interactive web application.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Status](https://img.shields.io/badge/Status-Complete-brightgreen?style=flat-square)

---

## 📌 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Project Structure](#-project-structure)
- [How It Works](#-how-it-works)
- [Getting Started](#-getting-started)
- [Usage](#-usage)
- [Screenshots](#-screenshots)
- [Technologies](#-technologies)

---

## 🧠 Overview

This project implements a **Dynamic Pathfinding Agent** in a Wumpus World-style environment. The agent does **not** know the locations of hazards at the start. Instead, it:

1. **Perceives** its surroundings (Breeze near Pits, Stench near Wumpus)
2. **Tells** a Propositional Logic Knowledge Base (KB) the rules derived from percepts
3. **Asks** the KB — via Resolution Refutation — whether adjacent cells are safe before moving
4. **Navigates** toward the gold while avoiding confirmed dangers

The entire system is served as a web application with a real-time visual dashboard.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🗺 Dynamic Grid | User-configurable grid size (4×4 up to 10×10) |
| 💣 Random Hazards | Pits (~20% of cells) and one Wumpus placed randomly each game |
| 👁 Percept Sensing | Breeze sensed adjacent to Pits; Stench adjacent to Wumpus |
| 🧩 Propositional KB | Full CNF Knowledge Base with `TELL` and `ASK` interface |
| 🔍 Resolution Refutation | From-scratch implementation — converts percepts to CNF, resolves clauses |
| 🟢 Safe Cell Inference | Agent proves `¬Pit ∧ ¬Wumpus` before committing to a move |
| 📊 Live Metrics | Inference steps, clause count, visited/safe cells — updated in real time |
| 🤖 Auto Navigation | One-click autonomous agent run with adjustable speed |
| 🕹 Manual Mode | Click any adjacent cell to move the agent yourself |

---

## 📁 Project Structure

```
wumpus-logic-agent/
│
├── logic_engine.py     # Propositional logic core: Literal + KnowledgeBase
│                       # → TELL (add CNF clauses)
│                       # → ASK  (Resolution Refutation)
│
├── wumpus_world.py     # World environment + KB-based agent
│                       # → Grid setup, hazard placement, percept generation
│                       # → Biconditional → CNF conversion and KB updates
│                       # → Safe-cell inference via KB queries
│
├── server.py           # Lightweight HTTP server (no dependencies)
│                       # → GET  /          → serves index.html
│                       # → GET  /state     → current game state (JSON)
│                       # → POST /new       → start new game {rows, cols}
│                       # → POST /move      → manual move    {row, col}
│                       # → POST /step      → agent auto-step
│
├── index.html          # Frontend: HTML + CSS + Vanilla JS (zero dependencies)
│                       # → Color-coded grid visualization
│                       # → Real-time metrics dashboard
│                       # → KB activity log
│
└── README.md
```

---

## ⚙ How It Works

### 1. Knowledge Base (`logic_engine.py`)

The `KnowledgeBase` class stores all knowledge as **CNF clauses** (frozensets of `Literal` objects).

**TELL** — adds clauses derived from percept observations:
```
No breeze at (2,1)  →  ¬P_1_1  ∧  ¬P_3_1  ∧  ¬P_2_2
Breeze at (1,2)     →  B_1_2
                        ¬B_1_2 ∨ P_0_2 ∨ P_2_2 ∨ P_1_1 ∨ P_1_3
                        ¬P_0_2 ∨ B_1_2  (for each neighbour)
```

**ASK** — proves a query via **Resolution Refutation**:
1. Negate the query and add to working clause set
2. Repeatedly resolve pairs of clauses
3. If an **empty clause** is derived → contradiction → query is **proved**
4. If fixpoint is reached with no contradiction → **unprovable**

### 2. World Environment (`wumpus_world.py`)

On each cell entry the agent:
- Senses breeze / stench from true hazard positions
- Calls `KB.tell()` with the biconditional CNF rules
- Calls `KB.ask()` on each unvisited neighbour to classify it as safe, pit, wumpus, or unknown

### 3. Agent Strategy

```
Priority 1 → Move to unvisited cell proved safe by KB
Priority 2 → Move to unvisited cell not confirmed dangerous
Priority 3 → Backtrack to a visited neighbour
```

### 4. REST API (`server.py`)

```
POST /new    {rows: 5, cols: 5}   → initialise world, return state
POST /move   {row: 2, col: 1}     → manual agent move, return state
POST /step   {}                   → one autonomous agent step, return state
GET  /state  →                    → current state (no side effects)
```

---

## 🚀 Getting Started

### Prerequisites

- Python **3.10 or higher**
- No external libraries required — uses only the Python standard library

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/wumpus-logic-agent.git
cd wumpus-logic-agent

# 2. Run the server
python server.py
```

### Open in Browser

```
http://localhost:8000
```

That's it. No `pip install`, no build step, no virtual environment needed.

---

## 🕹 Usage

| Action | How |
|---|---|
| Start new game | Set rows/cols → click **New Game** |
| Move manually | Click any adjacent cell on the grid |
| One agent step | Click **Agent Step** |
| Autonomous run | Click **Auto Run** (adjust speed with slider) |
| Stop auto run | Click **Stop** |

### Grid Cell Colors

| Color | Meaning |
|---|---|
| 🟡 Yellow | Agent's current position |
| 🔵 Dark Blue | Visited cell |
| 🟢 Dark Green | Safe (KB proved: no pit, no wumpus) |
| ⬛ Near-black | Unknown / unvisited |
| 🔴 Dark Red | Confirmed Pit (inferred or revealed) |
| 🟣 Dark Purple | Confirmed Wumpus (inferred or revealed) |

### Percept Icons (shown inside visited cells)

| Icon | Meaning |
|---|---|
| 💨 | Breeze — a pit is adjacent |
| 🦨 | Stench — the wumpus is adjacent |
| 🤖 | Agent |
| ⚠️ | KB inferred this is likely a pit |
| ☠️ | KB inferred the wumpus is here |
| 🏆 | Gold (revealed on win) |

---

## 🛠 Technologies

| Layer | Technology |
|---|---|
| Logic Engine | Python — implemented from scratch |
| Web Server | Python `http.server` (stdlib only) |
| Frontend | Vanilla HTML5 / CSS3 / JavaScript |
| Fonts | Google Fonts — Orbitron, Share Tech Mono |

---

## 📄 License

This project is licensed under the MIT License.

---

*Built as a Knowledge-Based Agent project — NUCES Chiniot-Faisalabad Campus*
