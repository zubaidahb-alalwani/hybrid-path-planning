"""Build the 15 Scopus component-pair queries (C2 AND Fa AND Fb) for Supplementary S2.

Scopus treats * as a truncation wildcard even inside quotes, so algorithm names that
contain a literal asterisk (A*, D* Lite, Theta*, RRT*, BIT*) are written without it.
"""
import itertools

C2 = '("path planning" OR "motion planning" OR "trajectory planning" OR "trajectory generation")'
F = {
 "F1": '("A-star" OR "A star" OR "A algorithm" OR Astar OR Dijkstra OR "D-star" OR "D star lite" OR "jump point search" OR "Theta-star" OR "Theta star" OR "state lattice" OR "fast marching")',
 "F2": '(RRT OR "RRT-star" OR "RRT star" OR "rapidly exploring random tree" OR "rapidly-exploring random tree" OR "probabilistic roadmap" OR PRM OR "batch informed trees")',
 "F3": '("dynamic window" OR DWA OR "potential field" OR APF OR "vector field histogram" OR "velocity obstacle" OR ORCA OR "timed elastic band")',
 "F4": '("model predictive control" OR MPC OR MPPI OR "trajectory optimization" OR CHOMP OR TrajOpt OR "B-spline optimization" OR "minimum snap" OR "quadratic programming")',
 "F5": '("genetic algorithm" OR "particle swarm" OR "ant colony" OR "grey wolf" OR "simulated annealing" OR "differential evolution" OR "artificial bee colony" OR "whale optimization")',
 "F6": '("reinforcement learning" OR "deep learning" OR "neural network" OR "imitation learning" OR fuzzy OR ANFIS)',
}
LIMITS = 'AND PUBYEAR > 2014 AND PUBYEAR < 2026 AND ( LIMIT-TO ( DOCTYPE , "ar" ) OR LIMIT-TO ( DOCTYPE , "cp" ) ) AND ( LIMIT-TO ( LANGUAGE , "English" ) )'

if __name__ == "__main__":
    lines = ["Scopus component-pair queries (paste each into Advanced document search)", ""]
    for a, b in itertools.combinations(sorted(F), 2):
        lines.append(f"H[{a[1]}+{b[1]}]  save the export as pair_{a}{b}.csv")
        lines.append(f"TITLE-ABS-KEY ( {C2} AND {F[a]} AND {F[b]} ) {LIMITS}")
        lines.append("")
    lines += ["Test before running (check that the first results are about A* / RRT*):",
              'TITLE-ABS-KEY ( "A algorithm" ) AND PUBYEAR > 2014 AND PUBYEAR < 2026',
              'TITLE-ABS-KEY ( "A star" OR "A-star" ) AND PUBYEAR > 2014 AND PUBYEAR < 2026']
    print("\n".join(lines))
