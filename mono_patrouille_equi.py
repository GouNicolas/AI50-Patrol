from collections import deque
import math
import heapq
import itertools

# circuit unique partage par tou les agent
circuit_global = []
objectifs_agents = {}
initialise = False


def initialisation(agents):
    global circuit_global, objectifs_agents, initialise

    circuit_global = []
    objectifs_agents = {}
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

    # 2. calcul des plus court chemin avec dijkstra pour tout le graphe
    distances = {}
    chemins = {}
    compteur = itertools.count()

    for origine in noeuds:
        dist = {origine: 0}
        precedent = {}
        file_d = [(0, next(compteur), origine)]

        while file_d:
            cout, _, noeud = heapq.heappop(file_d)

            if cout > dist[noeud]:
                continue

            for l in noeud.liaisons:
                voisin = l.cible
                nouveau_cout = cout + l.poids

                if nouveau_cout < dist.get(voisin, float("inf")):
                    dist[voisin] = nouveau_cout
                    precedent[voisin] = noeud
                    heapq.heappush(
                        file_d,
                        (nouveau_cout, next(compteur), voisin)
                    )

        distances[origine] = dist
        chemins[origine] = {}

        for arrivee in noeuds:
            if arrivee not in dist:
                continue

            chemin = [arrivee]
            courant = arrivee

            while courant != origine:
                courant = precedent[courant]
                chemin.append(courant)

            chemin.reverse()
            chemins[origine][arrivee] = chemin

    # 3. tournee TSP globale par plus proche voisin
    depart_principal = next(
        (a.noeud_actuel for a in agents if a.noeud_actuel in tous_noeuds),
        noeuds[0]
    )

    non_visites = set(noeuds)
    non_visites.remove(depart_principal)
    tour = [depart_principal]
    courant = depart_principal

    while non_visites:
        suivant = min(
            non_visites,
            key=lambda n: distances[courant].get(n, float("inf"))
        )
        tour.append(suivant)
        non_visites.remove(suivant)
        courant = suivant

    # opti 2-opt sur le grand tour
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

                ancien = distances[a].get(b, float("inf")) + distances[c].get(d, float("inf"))
                nouveau = distances[a].get(c, float("inf")) + distances[b].get(d, float("inf"))

                if nouveau < ancien:
                    tour[i:j + 1] = reversed(tour[i:j + 1])
                    amelioration = True

    # 4. developpement de la boucle avec refermeture propre
    parcours = []

    for i in range(len(tour)):
        origine = tour[i]
        arrivee = tour[(i + 1) % len(tour)]

        chemin = chemins[origine].get(arrivee)
        if not chemin:
            chemin = [origine, arrivee]

        if i == 0:
            parcours.extend(chemin)
        else:
            parcours.extend(chemin[1:])

    circuit_global = parcours

    # 5. calcul des segments et de la longueur totale du circuit pour un espacement 100% proportionnel au poid
    n_etapes = len(circuit_global)
    segments = []
    longueur_totale = 0.0

    for j in range(n_etapes):
        u = circuit_global[j]
        v = circuit_global[(j + 1) % n_etapes]

        # recherche du poid reel de la liaison
        liaison = next((l for l in u.liaisons if l.cible == v), None)
        poids = liaison.poids if liaison else math.dist((u.x, u.y), (v.x, v.y))

        segments.append((j, u, v, poids, longueur_totale))
        longueur_totale += poids

    nb_agents = len(agents)

    for i, agent in enumerate(agents):
        # distance cible de cet agent le long du circuit
        distance_cible = (i * longueur_totale) / nb_agents

        # trouver le segment exact ou se trouve cette distance
        segment_choisi = segments[-1]
        for seg in segments:
            j, u, v, poids, start_dist = seg
            if start_dist <= distance_cible < start_dist + poids:
                segment_choisi = seg
                break

        j, u, v, poids, start_dist = segment_choisi
        reste = distance_cible - start_dist
        ratio = (reste / poids) if poids > 0 else 0.0

        # objectif suivant dans le circuit
        objectifs_agents[agent.id] = (j + 1) % n_etapes

        # positionnement direct sur l'arete entre u et v
        agent.noeud_actuel = u
        agent.noeud_depart_trajet = u
        agent.destination = v

        liaison_exacte = next((l for l in u.liaisons if l.cible == v), None)
        poids_reel = liaison_exacte.poids if liaison_exacte else poids

        agent.temps_trajet_total = (
            poids_reel / agent.vitesse
            if agent.vitesse > 0
            else float("inf")
        )
        agent.temps_trajet_ecoule = ratio * agent.temps_trajet_total
        agent.x = u.x + (v.x - u.x) * ratio
        agent.y = u.y + (v.y - u.y) * ratio

    initialise = True

    print("\napres init circuit unique distance reelle :")
    print("longueur totale du circuit :", round(longueur_totale, 2))
    print("nb agents places sur aretes :", nb_agents)
    print("init :", initialise)


def choisir_destination(agent, agents, TEMPS_SIMULATION):
    global initialise

    if not initialise:
        initialisation(agents)

    if agent.destination is not None:
        return

    noeud_actuel = agent.noeud_actuel

    if noeud_actuel is None:
        return

    if len(circuit_global) < 2:
        return

    idx = objectifs_agents.get(agent.id, 1)
    nb_etapes = len(circuit_global)

    if idx >= nb_etapes:
        idx = 0

    cible = circuit_global[idx]

    # securite : si la cible est egale au noeud actuel, on avance direct l'index
    if noeud_actuel == cible:
        idx = (idx + 1) % nb_etapes
        cible = circuit_global[idx]

    # si l'agent est arrive a sa cible, passer a l'etape suivante sur le circuit global
    if noeud_actuel == cible:
        idx = (idx + 1) % nb_etapes
        cible = circuit_global[idx]

    # verif si cible accessible direct
    liaison_trouvee = next(
        (l for l in noeud_actuel.liaisons if l.cible == cible),
        None
    )

    # si pas de liaison directe dans le circuit, on cherche un voisin direct du circuit pour avancer sans bloquer
    if liaison_trouvee is None:
        # on cherche dans le circuit l'index le plus proche qui a une liaison directe
        for offset in range(1, nb_etapes):
            test_idx = (idx + offset) % nb_etapes
            test_cible = circuit_global[test_idx]
            liaison_trouvee = next(
                (l for l in noeud_actuel.liaisons if l.cible == test_cible),
                None
            )
            if liaison_trouvee is not None:
                idx = test_idx
                cible = test_cible
                break

    if liaison_trouvee is None:
        print(
            f"[test blocage] agent {agent.id} vraiment bloque : "
            f"pos={noeud_actuel.id}, "
            f"cible={cible.id}, idx={idx}"
        )
        return

    objectifs_agents[agent.id] = (idx + 1) % nb_etapes

    agent.destination = cible
    agent.noeud_depart_trajet = noeud_actuel
    agent.temps_trajet_total = (
        liaison_trouvee.poids / agent.vitesse
        if agent.vitesse > 0
        else float("inf")
    )
    agent.temps_trajet_ecoule = 0.0
