from collections import deque
import math
import heapq
import itertools

# circuit de patrouille par id d'agent
circuits_agents = {}
objectifs_agents = {}

# lien noeud -> cluster
clusters_noeuds = {}

initialise = False


def initialisation(agents):
    global circuits_agents, objectifs_agents
    global clusters_noeuds, initialise

    circuits_agents = {}
    objectifs_agents = {}
    clusters_noeuds = {}
    initialise = False

    if not agents:
        return

    # 1. recup de tou les noeud accessible depuis les agent
    tous_noeuds = set()
    file = deque(
        a.noeud_actuel for a in agents
        if a.noeud_actuel is not None
    )

    while file:
        noeud = file.popleft()

        if noeud in tous_noeuds:
            continue

        tous_noeuds.add(noeud)

        for l in noeud.liaisons:
            if l.cible not in tous_noeuds:
                file.append(l.cible)

    noeuds = list(tous_noeuds)

    if not noeuds:
        return

    if len(agents) > len(noeuds):
        print("attension : plus d'agent que de noeud")

    # 2. choix des point de depart eloigne
    nb_clusters = min(len(agents), len(noeuds))

    premier_depart = next(
        (a.noeud_actuel for a in agents if a.noeud_actuel in tous_noeuds),
        noeuds[0]
    )

    graines = [premier_depart]

    while len(graines) < nb_clusters:
        candidats = [n for n in noeuds if n not in graines]

        suivant = max(
            candidats,
            key=lambda n: min(
                (n.x - g.x) ** 2 + (n.y - g.y) ** 2
                for g in graines
            )
        )

        graines.append(suivant)

    # 3. repartition des clusteur en bfs
    groupes = {a.id: set() for a in agents}
    proprietaire = {}
    file = deque()

    for i, agent in enumerate(agents):
        depart = graines[i % len(graines)]

        # si 2 agent ont le meme depart ils partagent le clusteur
        if depart not in proprietaire:
            proprietaire[depart] = agent.id
            groupes[agent.id].add(depart)
            file.append((depart, agent.id))

    while file:
        noeud, id_agent = file.popleft()

        for l in noeud.liaisons:
            voisin = l.cible

            if voisin in tous_noeuds and voisin not in proprietaire:
                proprietaire[voisin] = id_agent
                groupes[id_agent].add(voisin)
                file.append((voisin, id_agent))

    # associe les agent qui partagent un meme depart au meme groupe
    for agent in agents:
        depart = graines[agents.index(agent) % len(graines)]
        id_proprietaire = proprietaire.get(depart)

        if id_proprietaire is not None and id_proprietaire != agent.id:
            groupes[agent.id] = groupes[id_proprietaire].copy()

    # 4. boucle dfs pr chaq clusteur
    def construire_parcours(depart, groupe):
        if len(groupe) <= 1:
            return [depart]

        # calcul du plus court chemin inter-clusteur
        distances = {}
        chemins = {}
        compteur = itertools.count()

        for origine in groupe:
            dist = {origine: 0}
            precedent = {}
            file = [(0, next(compteur), origine)]

            while file:
                cout, _, noeud = heapq.heappop(file)

                if cout > dist[noeud]:
                    continue

                for l in noeud.liaisons:
                    voisin = l.cible

                    if voisin not in groupe:
                        continue

                    nouveau_cout = cout + l.poids

                    if nouveau_cout < dist.get(voisin, float("inf")):
                        dist[voisin] = nouveau_cout
                        precedent[voisin] = noeud
                        heapq.heappush(
                            file,
                            (nouveau_cout, next(compteur), voisin)
                        )

            distances[origine] = dist
            chemins[origine] = {}

            for arrivee in groupe:
                if arrivee not in dist:
                    continue

                chemin = [arrivee]
                courant = arrivee

                while courant != origine:
                    courant = precedent[courant]
                    chemin.append(courant)

                chemin.reverse()
                chemins[origine][arrivee] = chemin

        # premiere boucle plus proche voisin
        non_visites = set(groupe)
        non_visites.remove(depart)
        tour = [depart]
        courant = depart

        while non_visites:
            suivant = min(
                non_visites,
                key=lambda n: distances[courant].get(n, float("inf"))
            )

            tour.append(suivant)
            non_visites.remove(suivant)
            courant = suivant

        # opti 2-opt sur la boucle
        amelioration = True

        while amelioration:
            amelioration = False
            n = len(tour)

            for i in range(1, n - 1):
                for j in range(i + 1, n):
                    a = tour[i - 1]
                    b = tour[i]
                    c = tour[j]
                    d = tour[(j + 1) % n]

                    ancien = distances[a][b] + distances[c][d]
                    nouveau = distances[a][c] + distances[b][d]

                    if nouveau < ancien:
                        tour[i:j + 1] = reversed(tour[i:j + 1])
                        amelioration = True

        # recontruction du parcours reel
        parcours = [tour[0]]

        for i in range(len(tour)):
            origine = tour[i]
            arrivee = tour[(i + 1) % len(tour)]

            chemin = chemins[origine][arrivee]
            parcours.extend(chemin[1:])

        for i in range(len(parcours) - 1):
            courant = parcours[i]
            suivant = parcours[i + 1]

            if not any(l.cible == suivant for l in courant.liaisons):
                print(
                    f"erreur circuit : "
                    f"{courant.id} -> {suivant.id} "
                    f"pas une liaison valide"
                )

        return parcours

    # 5. assignasion des circuit + tp des bot
    for agent in agents:
        depart = graines[agents.index(agent) % len(graines)]
        id_cluster = proprietaire.get(depart, agent.id)
        groupe = groupes.get(id_cluster, set())

        if not groupe:
            continue

        circuit = construire_parcours(depart, groupe)

        if not circuit:
            continue

        circuits_agents[agent.id] = circuit
        objectifs_agents[agent.id] = 1 if len(circuit) > 1 else 0

        # tp au depart du circuit
        agent.noeud_actuel = circuit[0]
        agent.x = circuit[0].x
        agent.y = circuit[0].y
        agent.destination = None
        agent.noeud_depart_trajet = circuit[0]
        agent.temps_trajet_total = 0.0
        agent.temps_trajet_ecoule = 0.0

    clusters_noeuds = proprietaire.copy()
    initialise = True

    for agent in agents:
        circuit = circuits_agents.get(agent.id, [])



def choisir_destination(agent, agents, TEMPS_SIMULATION):
    global initialise

    if not initialise:
        initialisation(agents)

    if agent.destination is not None:
        return

    noeud_actuel = agent.noeud_actuel

    if noeud_actuel is None:
        return

    circuit = circuits_agents.get(agent.id, [])

    if len(circuit) < 2:
        return

    idx = objectifs_agents.get(agent.id, 1)

    if idx >= len(circuit):
        idx = 1

    # si l'agent est arrive a sa cible, passer a l'etape suivante
    if noeud_actuel == circuit[idx]:
        idx = (idx + 1) % len(circuit)

        if idx == 0:
            idx = 1

    # si l'index ne correspond pas a la position reelle, chercher la prochaine occurrence
    elif circuit[idx - 1] != noeud_actuel:
        positions = [
            i for i, noeud in enumerate(circuit)
            if noeud == noeud_actuel and i > 0
        ]

        if positions:
            idx = (positions[0] + 1) % len(circuit)

            if idx == 0:
                idx = 1

    cible = circuit[idx]

    # verif si cible accessible direct
    liaison_trouvee = next(
        (l for l in noeud_actuel.liaisons if l.cible == cible),
        None
    )

    if liaison_trouvee is None:
        print(
            f"[debug] agent={agent.id} | "
            f"pos={agent.noeud_actuel.id if agent.noeud_actuel else None} | "
            f"debut_circuit={circuit[0].id if circuit else None}"
        )

        print(
            f"agent {agent.id} bloque : "
            f"pos={noeud_actuel.id}, "
            f"cible={cible.id}, idx={idx}"
        )

        circuit = circuits_agents.get(agent.id, [])
        print("circuit :", [n.id for n in circuit])
        print("position actuelle :", agent.noeud_actuel.id)
        print("cible demandee :", cible.id)

        return

    objectifs_agents[agent.id] = idx

    agent.destination = cible
    agent.noeud_depart_trajet = noeud_actuel
    agent.temps_trajet_total = (
        liaison_trouvee.poids / agent.vitesse
        if agent.vitesse > 0
        else float("inf")
    )
    agent.temps_trajet_ecoule = 0.0










































