"""
wumpus_world.py
===============
Wumpus World Environment + Knowledge-Based Agent.

Depends on: logic_engine.py  (Literal, KnowledgeBase)

Classes
-------
WumpusWorld   – Grid environment: hazard placement, percept generation,
                KB integration, agent navigation.
"""

import random
from logic_engine import Literal, KnowledgeBase


# ─────────────────────────────────────────────────────────────────────────────
# WUMPUS WORLD
# ─────────────────────────────────────────────────────────────────────────────

class WumpusWorld:
    """
    Wumpus World environment with an embedded Knowledge-Based Agent.

    Grid coordinates: (row, col) with (0,0) at the top-left.

    Hazard rules
    ------------
    Pits    – ~20 % of non-start cells; adjacent cells produce a Breeze.
    Wumpus  – exactly one; adjacent cells produce a Stench.
    Gold    – exactly one; collected on entry (win condition).

    KB rules (biconditional, converted to CNF)
    ------------------------------------------
    B_{r,c}  ⟺  ⋁  P_{nr,nc}   for each neighbour (nr,nc)
    S_{r,c}  ⟺  ⋁  W_{nr,nc}   for each neighbour (nr,nc)

    When no breeze/stench: each neighbour cell gets a ¬P / ¬W clause.
    """

    # ── construction ─────────────────────────────────────────────────────────

    def __init__(self, rows: int, cols: int):
        self.rows: int = rows
        self.cols: int = cols

        # True hazard locations (hidden from agent until game over)
        self.pits:   set[tuple[int, int]] = set()
        self.wumpus: tuple[int, int]      = (-1, -1)
        self.gold:   tuple[int, int]      = (-1, -1)

        # Agent state
        self.agent_pos: tuple[int, int] = (0, 0)

        # Inference state
        self.visited:           set[tuple[int, int]] = set()
        self.safe:              set[tuple[int, int]] = set()
        self.confirmed_pit:     set[tuple[int, int]] = set()
        self.confirmed_wumpus:  set[tuple[int, int]] = set()
        self.percepts:          dict[tuple, dict]    = {}   # pos → {breeze, stench}

        # Knowledge Base
        self.kb: KnowledgeBase = KnowledgeBase()

        # Status
        self.game_over: bool = False
        self.won:       bool = False
        self.message:   str  = ""

        self._place_hazards()

    # ── public interface ──────────────────────────────────────────────────────

    def move_agent(self, target_r: int, target_c: int) -> dict:
        """
        Move the agent to (target_r, target_c).

        The target must be adjacent to the current position.
        Returns the current game state dict.
        """
        if self.game_over:
            return self.state()

        target = (target_r, target_c)
        if target not in self._neighbors(*self.agent_pos):
            self.message = "Invalid move: target cell is not adjacent."
            return self.state()

        self.agent_pos = target
        self._resolve_entry(target)
        return self.state()

    def agent_step(self) -> dict:
        """
        Autonomously move the agent one step using KB-guided strategy:

        Priority 1 – Unvisited safe neighbour (KB proved safe).
        Priority 2 – Unvisited neighbour not confirmed dangerous.
        Priority 3 – Backtrack to any visited neighbour.
        """
        if self.game_over:
            return self.state()

        neighbors = self._neighbors(*self.agent_pos)

        # P1 – unvisited + KB-safe
        for n in neighbors:
            if n not in self.visited and n in self.safe:
                return self.move_agent(*n)

        # P2 – unvisited + not confirmed dangerous
        for n in neighbors:
            if (n not in self.visited
                    and n not in self.confirmed_pit
                    and n not in self.confirmed_wumpus):
                return self.move_agent(*n)

        # P3 – backtrack
        for n in neighbors:
            if n in self.visited:
                self.agent_pos = n
                self.message   = f"Backtracked to ({n[0]},{n[1]})."
                return self.state()

        self.message = "Agent is stuck — no safe moves available."
        return self.state()

    def state(self) -> dict:
        """
        Serialise the current world state to a JSON-friendly dict.

        Hazard positions are revealed only after game-over.
        """
        return {
            # Grid dimensions
            "rows":  self.rows,
            "cols":  self.cols,

            # Agent
            "agent": list(self.agent_pos),

            # Inference results
            "visited":           [list(p) for p in self.visited],
            "safe":              [list(p) for p in self.safe],
            "confirmed_pit":     [list(p) for p in self.confirmed_pit],
            "confirmed_wumpus":  [list(p) for p in self.confirmed_wumpus],

            # Percept map  {"r,c": {breeze, stench}}
            "percepts":          {f"{r},{c}": v for (r, c), v in self.percepts.items()},
            "current_percepts":  self.percepts.get(self.agent_pos, {}),

            # Metrics
            "inference_steps":   self.kb.inference_steps,
            "clause_count":      self.kb.clause_count,

            # Game status
            "game_over": self.game_over,
            "won":       self.won,
            "message":   self.message,

            # Revealed only on game-over
            "pits":   [list(p) for p in self.pits]  if self.game_over else [],
            "wumpus": list(self.wumpus)               if self.game_over else [],
            "gold":   list(self.gold),
        }

    # ── private: setup ────────────────────────────────────────────────────────

    def _place_hazards(self) -> None:
        """Randomly place pits (~20 %), one Wumpus, and the gold."""
        all_cells = [
            (r, c)
            for r in range(self.rows)
            for c in range(self.cols)
            if (r, c) != (0, 0)
        ]
        random.shuffle(all_cells)

        # Pits
        n_pits      = max(1, int(len(all_cells) * 0.20))
        self.pits   = set(all_cells[:n_pits])

        # Wumpus — not in a pit
        rest        = [c for c in all_cells if c not in self.pits]
        self.wumpus = rest[0]

        # Gold — not in a pit or on the wumpus
        gold_pool   = [c for c in rest[1:] if c != self.wumpus]
        self.gold   = random.choice(gold_pool) if gold_pool else (0, 1)

        # Agent starts at (0,0) — mark safe and enter
        self.safe.add((0, 0))
        self._enter_cell((0, 0))

    # ── private: navigation ───────────────────────────────────────────────────

    def _neighbors(self, r: int, c: int) -> list[tuple[int, int]]:
        """Return valid 4-directional neighbours of (r, c)."""
        result = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.rows and 0 <= nc < self.cols:
                result.append((nr, nc))
        return result

    def _resolve_entry(self, pos: tuple[int, int]) -> None:
        """Handle consequences of the agent entering a cell."""
        if pos in self.pits:
            self.visited.add(pos)
            self.confirmed_pit.add(pos)
            self.game_over = True
            self.won       = False
            self.message   = "💀 Fell into a pit! Game over."
            return

        if pos == self.wumpus:
            self.visited.add(pos)
            self.confirmed_wumpus.add(pos)
            self.game_over = True
            self.won       = False
            self.message   = "💀 Eaten by the Wumpus! Game over."
            return

        if pos == self.gold:
            self._enter_cell(pos)
            self.game_over = True
            self.won       = True
            self.message   = "🏆 Found the gold! You win!"
            return

        self._enter_cell(pos)
        self.message = f"Moved to ({pos[0]}, {pos[1]})."

    def _enter_cell(self, pos: tuple[int, int]) -> None:
        """Sense percepts, update KB, infer safe / dangerous neighbours."""
        r, c = pos
        self.visited.add(pos)
        self.safe.add(pos)

        # ── sense ────────────────────────────────────────────────────────────
        neighbors = self._neighbors(r, c)
        breeze    = any(n in self.pits   for n in neighbors)
        stench    = any(n == self.wumpus for n in neighbors)
        self.percepts[pos] = {"breeze": breeze, "stench": stench}

        # ── TELL KB ──────────────────────────────────────────────────────────
        self._tell_kb(r, c, neighbors, breeze, stench)

        # ── ASK KB about unvisited neighbours ────────────────────────────────
        for (nr, nc) in neighbors:
            if (nr, nc) not in self.visited:
                self._infer_cell(nr, nc)

    def _tell_kb(
        self,
        r: int,
        c: int,
        neighbors: list[tuple[int, int]],
        breeze: bool,
        stench: bool,
    ) -> None:
        """
        Encode percept observations as CNF clauses and TELL the KB.

        Biconditional  B_{r,c} ⟺ ⋁ P_{n}
        is split into:
            (B_{r,c} ⟹ ⋁ P_{n})  →  ¬B ∨ P1 ∨ P2 ∨ …
            (each P_{n} ⟹ B)      →  ¬Pn ∨ B

        When no breeze / stench, each neighbour gets ¬P / ¬W directly.
        """
        b_lit = Literal(f"B_{r}_{c}")
        s_lit = Literal(f"S_{r}_{c}")

        pit_lits    = [Literal(f"P_{nr}_{nc}") for (nr, nc) in neighbors]
        wumpus_lits = [Literal(f"W_{nr}_{nc}") for (nr, nc) in neighbors]

        # ── Breeze / Pit ─────────────────────────────────────────────────────
        if breeze:
            self.kb.tell([[b_lit]])
            # B ⟹ (P1 ∨ P2 ∨ …)
            self.kb.tell([[b_lit.negate()] + pit_lits])
            # each Pn ⟹ B
            for pl in pit_lits:
                self.kb.tell([[pl.negate(), b_lit]])
        else:
            self.kb.tell([[b_lit.negate()]])
            # No breeze → no pit in any neighbour
            for pl in pit_lits:
                self.kb.tell([[pl.negate()]])

        # ── Stench / Wumpus ───────────────────────────────────────────────────
        if stench:
            self.kb.tell([[s_lit]])
            self.kb.tell([[s_lit.negate()] + wumpus_lits])
            for wl in wumpus_lits:
                self.kb.tell([[wl.negate(), s_lit]])
        else:
            self.kb.tell([[s_lit.negate()]])
            for wl in wumpus_lits:
                self.kb.tell([[wl.negate()]])

    def _infer_cell(self, nr: int, nc: int) -> None:
        """
        ASK the KB whether (nr, nc) is safe or dangerous,
        and update the appropriate inference sets.
        """
        pit_lit    = Literal(f"P_{nr}_{nc}")
        wumpus_lit = Literal(f"W_{nr}_{nc}")

        no_pit    = self.kb.ask(pit_lit.negate())
        no_wumpus = self.kb.ask(wumpus_lit.negate())

        if no_pit and no_wumpus:
            self.safe.add((nr, nc))
        elif self.kb.ask(pit_lit):
            self.confirmed_pit.add((nr, nc))
        elif self.kb.ask(wumpus_lit):
            self.confirmed_wumpus.add((nr, nc))
