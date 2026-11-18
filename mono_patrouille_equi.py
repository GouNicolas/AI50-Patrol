from collections import deque
import math
import heapq
import itertools

# circuit unique partage par tou agent
Circuit_global = []
Objectifs_agent = {}
Initialise = False


def initialisation(Agent_liste):
    global Circuit_global, Objectifs_agent, Initialise

    Circuit_global = []
    Objectifs_agent = {}
    Initialise = False

    if not Agent_liste:
        return

    # 1. recup de tou noeud accessible depui agent
    Tous_noeud = set()
    File = deque(
        a.noeud_actuel for a in Agent_liste
        if a.noeud_actuel is not None
    )

    while File:
        noeud = File.popleft()

        if noeud in Tous_noeud:
            continue

        Tous_noeud.add(noeud)

        for l in noeud.liaison:
            if l.cible not in Tous_noeud:
                File.append(l.cible)

    Noeud_liste = list(Tous_noeud)

    if not Noeud_liste:
        return

    if len(Agent_liste) > len(Noeud_liste):
        print("attension : plu d'agent ke de noeud")

    # 2. calcul plus cour chemin avec dijkstra pr tt graphe
    Distances = {}
    Chemins = {}
    Compteur = itertools.count()

    for origine in Noeud_liste:
        dist = {origine: 0}
        precedent = {}
        File_d = [(0, next(Compteur), origine)]

        while File_d:
            cout, _, noeud = heapq.heappop(File_d)

            if cout > dist[noeud]:
                continue

            for l in noeud.liaison:
                voisin = l.cible
                nouveau_cout = cout + l.poid

                if nouveau_cout < dist.get(voisin, float("inf")):
                    dist[voisin] = nouveau_cout
                    precedent[voisin] = noeud
                    heapq.heappush(
                        File_d,
                        (nouveau_cout, next(Compteur), voisin)
                    )

        Distances[origine] = dist
        Chemins[origine] = {}

        for arrivee in Noeud_liste:
            if arrivee not in dist:
                continue

            chemin = [arrivee]
            courant = arrivee

            while courant != origine:
                courant = precedent[courant]
                chemin.append(courant)

            chemin.reverse()
            Chemins[origine][arrivee] = chemin

    # 3. tournee tsp globale par plus proche voisin
    Depart_principal = next(
        (a.noeud_actuel for a in Agent_liste if a.noeud_actuel in Tous_noeud),
        Noeud_liste[0]
    )

    Non_visite = set(Noeud_liste)
    Non_visite.remove(Depart_principal)
    Tour = [Depart_principal]
    courant = Depart_principal

    while Non_visite:
        suivant = min(
            Non_visite,
            key=lambda n: Distances[courant].get(n, float("inf"))
        )
        Tour.append(suivant)
        Non_visite.remove(suivant)
        courant = suivant

    # opti 2-opt sur le grand tour
    Amelioration = True
    while Amelioration:
        Amelioration = False
        n = len(Tour)

        for i in range(1, n - 1):
            for j in range(i + 1, n):
                a = Tour[i - 1]
                b = Tour[i]
                c = Tour[j]
                d = Tour[(j + 1) % n]

                ancien = Distances[a].get(b, float("inf")) + Distances[c].get(d, float("inf"))
                nouveau = Distances[a].get(c, float("inf")) + Distances[b].get(d, float("inf"))

                if nouveau < ancien:
                    Tour[i:j + 1] = reversed(Tour[i:j + 1])
                    Amelioration = True

    # 4. dev de boucle avec refermeture propre
    Parcours = []

    for i in range(len(Tour)):
        origine = Tour[i]
        arrivee = Tour[(i + 1) % len(Tour)]

        chemin = Chemins[origine].get(arrivee)
        if not chemin:
            chemin = [origine, arrivee]

        if i == 0:
            Parcours.extend(chemin)
        else:
            Parcours.extend(chemin[1:])

    Circuit_global = Parcours

    # 5. calcul segment et longueur totale circuit pr espacement proportionnel au poid
    N_etape = len(Circuit_global)
    Segments = []
    Longueur_totale = 0.0

    for j in range(N_etape):
        u = Circuit_global[j]
        v = Circuit_global[(j + 1) % N_etape]

        liaison = next((l for l in u.liaison if l.cible == v), None)
        poid = liaison.poid if liaison else math.dist((u.x, u.y), (v.x, v.y))

        Segments.append((j, u, v, poid, Longueur_totale))
        Longueur_totale += poid

    Nb_agent = len(Agent_liste)

    for i, agent in enumerate(Agent_liste):
        Distance_cible = (i * Longueur_totale) / Nb_agent

        Segment_choisi = Segments[-1]
        for seg in Segments:
            j, u, v, poid, Start_dist = seg
            if Start_dist <= Distance_cible < Start_dist + poid:
                Segment_choisi = seg
                break

        j, u, v, poid, Start_dist = Segment_choisi
        Reste = Distance_cible - Start_dist
        Ratio = (Reste / poid) if poid > 0 else 0.0

        Objectifs_agent[agent.id] = (j + 1) % N_etape

        agent.noeud_actuel = u
        agent.noeud_depart_trajet = u
        agent.destination = v

        Liaison_exacte = next((l for l in u.liaison if l.cible == v), None)
        Poid_reel = Liaison_exacte.poid if Liaison_exacte else poid

        agent.temps_trajet_total = (
            Poid_reel / agent.vitesse
            if agent.vitesse > 0
            else float("inf")
        )
        agent.temps_trajet_ecoule = Ratio * agent.temps_trajet_total
        agent.x = u.x + (v.x - u.x) * Ratio
        agent.y = u.y + (v.y - u.y) * Ratio

    Initialise = True

    print("\napres init circuit unique distance reelle :")
    print("longueur totale circuit :", round(Longueur_totale, 2))
    print("nb agent place sur arete :", Nb_agent)
    print("init :", Initialise)


def choisir_destination(agent, Agent_liste, TEMPS_SIMULATION):
    global Initialise

    if not Initialise:
        initialisation(Agent_liste)

    if agent.destination is not None:
        return

    noeud_actuel = agent.noeud_actuel

    if noeud_actuel is None:
        return

    if len(Circuit_global) < 2:
        return

    idx = Objectifs_agent.get(agent.id, 1)
    N_etape = len(Circuit_global)

    if idx >= N_etape:
        idx = 0

    cible = Circuit_global[idx]

    if noeud_actuel == cible:
        idx = (idx + 1) % N_etape
        cible = Circuit_global[idx]

    if noeud_actuel == cible:
        idx = (idx + 1) % N_etape
        cible = Circuit_global[idx]

    Liaison_trouvee = next(
        (l for l in noeud_actuel.liaison if l.cible == cible),
        None
    )

    if Liaison_trouvee is None:
        for offset in range(1, N_etape):
            test_idx = (idx + offset) % N_etape
            test_cible = Circuit_global[test_idx]
            Liaison_trouvee = next(
                (l for l in noeud_actuel.liaison if l.cible == test_cible),
                None
            )
            if Liaison_trouvee is not None:
                idx = test_idx
                cible = test_cible
                break

    if Liaison_trouvee is None:
        print(
            f"[test blocage] agent {agent.id} vrémen bloke : "
            f"pos={noeud_actuel.id}, "
            f"cible={cible.id}, idx={idx}"
        )
        return

    Objectifs_agent[agent.id] = (idx + 1) % N_etape

    agent.destination = cible
    agent.noeud_depart_trajet = noeud_actuel
    agent.temps_trajet_total = (
        Liaison_trouvee.poid / agent.vitesse
        if agent.vitesse > 0
        else float("inf")
    )
    agent.temps_trajet_ecoule = 0.0
