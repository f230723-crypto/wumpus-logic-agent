"""
logic_engine.py
===============
Propositional Logic Engine for the Wumpus World Agent.

Contains:
  - Literal       : A propositional variable (positive or negated)
  - KnowledgeBase : CNF clause store with TELL / ASK via Resolution Refutation
"""


# ─────────────────────────────────────────────────────────────────────────────
# LITERAL
# ─────────────────────────────────────────────────────────────────────────────

class Literal:
    """
    A propositional literal, e.g. P_2_1 or ¬P_2_1.

    Usage:
        p = Literal("P_2_1")           # positive literal
        not_p = p.negate()             # negated literal
        not_p2 = Literal("P_2_1", negated=True)
    """

    def __init__(self, name: str, negated: bool = False):
        self.name    = name
        self.negated = negated

    def negate(self) -> "Literal":
        """Return the complement of this literal."""
        return Literal(self.name, not self.negated)

    # ── equality & hashing so literals work inside sets / frozensets ──────────
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Literal):
            return NotImplemented
        return self.name == other.name and self.negated == other.negated

    def __hash__(self) -> int:
        return hash((self.name, self.negated))

    def __repr__(self) -> str:
        prefix = "¬" if self.negated else ""
        return f"{prefix}{self.name}"


# ─────────────────────────────────────────────────────────────────────────────
# KNOWLEDGE BASE
# ─────────────────────────────────────────────────────────────────────────────

class KnowledgeBase:
    """
    Propositional Logic Knowledge Base stored in Conjunctive Normal Form (CNF).

    Each clause is a frozenset of Literal objects.
    The whole KB is the conjunction (AND) of all clauses.

    Public API
    ----------
    tell(cnf_clauses)        Add new clauses to the KB.
    ask(query: Literal)      Prove query via Resolution Refutation.
    reset()                  Clear everything.

    Metrics
    -------
    inference_steps  – incremented once per resolution attempt.
    clause_count     – number of clauses currently in the KB.
    """

    def __init__(self):
        self._clauses: list[frozenset]  = []   # CNF clause store
        self.inference_steps: int       = 0

    # ── public ────────────────────────────────────────────────────────────────

    @property
    def clause_count(self) -> int:
        return len(self._clauses)

    def tell(self, cnf_clauses: list[list | set]) -> None:
        """
        Add clauses (each a list / set of Literals) to the KB.
        Duplicate clauses are silently ignored.
        """
        for raw in cnf_clauses:
            clause = frozenset(raw)
            if clause not in self._clauses:
                self._clauses.append(clause)

    def ask(self, query: Literal) -> bool:
        """
        Resolution Refutation:
            Prove `query` by showing KB ∪ {¬query} is unsatisfiable.

        Returns True  if query is entailed by the KB.
        Returns False if it cannot be proved (open-world assumption).
        """
        self.inference_steps += 1

        # Working set = KB + negated query
        negated_query = frozenset([query.negate()])
        working       = list(self._clauses) + [negated_query]
        seen           = {frozenset(c) for c in working}

        while True:
            new_found = False

            # Try every pair of clauses
            for i in range(len(working)):
                for j in range(i + 1, len(working)):
                    resolvents = self._resolve(working[i], working[j])

                    for resolvent in resolvents:
                        self.inference_steps += 1

                        if len(resolvent) == 0:
                            # Empty clause → contradiction → query is proved
                            return True

                        if resolvent not in seen:
                            seen.add(resolvent)
                            working.append(resolvent)
                            new_found = True

            if not new_found:
                # Fixpoint reached without contradiction → cannot prove query
                return False

    def reset(self) -> None:
        """Clear the KB and reset counters."""
        self._clauses        = []
        self.inference_steps = 0

    # ── private ───────────────────────────────────────────────────────────────

    @staticmethod
    def _resolve(c1: frozenset, c2: frozenset) -> list[frozenset]:
        """
        Standard propositional resolution.

        For each literal L in c1 whose complement ¬L appears in c2,
        produce the resolvent: (c1 − {L}) ∪ (c2 − {¬L}).
        """
        resolvents = []
        for lit in c1:
            neg_lit = lit.negate()
            if neg_lit in c2:
                merged = (c1 - {lit}) | (c2 - {neg_lit})
                resolvents.append(frozenset(merged))
        return resolvents
